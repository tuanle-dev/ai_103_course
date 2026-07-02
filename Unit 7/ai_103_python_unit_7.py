"""
UNIT 7: Azure AI Search (Part 2) - From Basic Indexing to Semantic Search with Vector Embeddings

NEW IN THIS UNIT:

1. Deploy a basic Azure AI Search service using Bicep, an infrastructure-as-code language that enables automated, repeatable deployments in Azure.
2. Design and create a search index with both traditional text fields and vector fields to support hybrid search capabilities.
3. Generate vector embeddings for document content using Azure OpenAI's text-embedding-3-small model, converting text into numerical representations that capture semantic meaning.
4. Upload and ingest documents with their corresponding embeddings into the index, preparing your data for both keyword-based and semantic search scenarios.
5. Perform hybrid search queries that combine traditional keyword search (BM25) with vector similarity search, delivering more relevant results by understanding intent and context.
6. Implement semantic reranking using a semantic configuration that prioritizes title and content fields, improving result relevance through language model-based reordering.
7. Assign role-based access control (RBAC) roles to users for the Azure AI Search resource, including:
    a. Search Service Contributor
    b. Search Index Data Contributor
    c. Search Index Data Reader
You will learn how to use the Azure CLI to grant these roles, enabling secure and appropriate access to search resources and data.

By completing these steps, you will gain hands-on experience with the full lifecycle of Azure AI Search: provisioning resources, modeling data with vector support, generating embeddings from LLMs, loading content, and building intelligent, semantic search solutions that understand user intent—moving beyond simple keyword matching to context-aware information discovery for enterprise applications.
"""

import os

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SimpleField,
    SearchableField,
    SearchField,
    SearchIndex,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AI_SEARCH_SERVICE_ENDPOINT = os.getenv("AI_SEARCH_SERVICE_ENDPOINT")
EMBEDDING_MODEL_DEPLOYMENT_NAME = os.getenv("EMBEDDING_MODEL_DEPLOYMENT_NAME")

INDEX_NAME = "unit_7_ai_search_index"

# =============================================================================
# AUTHENTICATION
# =============================================================================

credential = DefaultAzureCredential()

token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
openai_client = OpenAI(base_url=AZURE_OPENAI_ENDPOINT, api_key=token_provider)

# =============================================================================
# AI SEARCH FUNCTIONS
# =============================================================================


def generate_embeddings(text):
    """Generate a vector embedding for the given text."""
    response = openai_client.embeddings.create(
        input=text, model=EMBEDDING_MODEL_DEPLOYMENT_NAME
    )
    embedding = response.data[0].embedding
    return embedding


def create_index():
    print(f"📋 Creating index '{INDEX_NAME}'...")

    # Define the index schema
    fields = [
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="title", type="Edm.String"),
        SearchableField(name="content", type="Edm.String"),
        SimpleField(name="category", type="Edm.String", filterable=True),
        # NEW: Vector field
        SearchField(
            name="content_vector",
            type="Collection(Edm.Single)",
            vector_search_dimensions=1536,  # For text-embedding-3-small
            vector_search_profile_name="my_vector_profile",
        ),
    ]

    # Configure the vector search algorithm
    # This example uses HNSW (Hierarchical Navigable Small World) algorithm for efficient vector similarity search.
    # You can choose other algorithms like IVF or PQ based on your requirements and index size.
    # The vector search profile specifies which algorithm configuration to use for vector search queries.
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="my_hnsw_config")],
        profiles=[
            VectorSearchProfile(
                name="my_vector_profile", algorithm_configuration_name="my_hnsw_config"
            )
        ],
    )

    # Configure semantic search with prioritized fields for better relevance when using semantic queries.
    # This configuration tells Azure AI Search to prioritize the 'title' field and then the 'content' field when reranking results for semantic search queries.
    # You can adjust the prioritized fields based on your data and search relevance needs.
    # The semantic configuration is required to enable semantic search capabilities, which use language models to understand user intent and context for improved search relevance.
    # Without this configuration, semantic search queries will not be able to rerank results based on the content of the fields, and you will only get keyword-based search results.
    semantic_config = SemanticConfiguration(
        name="my_semantic_config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")],
        ),
    )
    semantic_search = SemanticSearch(
        configurations=[semantic_config]  # Pass your config in a SemanticSearch wrapper
    )

    # Create the index with the new vector configuration and semantic configuration
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    # Create the index client
    index_client = SearchIndexClient(AI_SEARCH_SERVICE_ENDPOINT, credential)

    # Check if the index already exists
    try:
        index_client.get_index(INDEX_NAME)
        print(f"ℹ️ Index '{INDEX_NAME}' already exists. Skipping creation.")
        return False
    except Exception:
        # If not found, create the index
        try:
            index_client.create_index(index)
            print(f"✓ Index '{INDEX_NAME}' created successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to create index: {e}")
            return False


def get_documents():

    documents = [
        {
            "id": "1",
            "title": "Azure Machine Learning Tutorial",
            "content": "Azure Machine Learning provides cloud-based environment for training and deploying ML models.",
            "category": "tutorial",
        },
        {
            "id": "2",
            "title": "Introduction to Python Programming",
            "content": "Python is a versatile programming language used for web development, data science, and AI.",
            "category": "programming",
        },
        {
            "id": "3",
            "title": "Azure AI Search Best Practices",
            "content": "Learn how to optimize Azure AI Search for performance and cost efficiency.",
            "category": "best-practices",
        },
        {
            "id": "4",
            "title": "Cloud Computing Fundamentals",
            "content": "Understanding cloud computing concepts including IaaS, PaaS, and SaaS.",
            "category": "fundamentals",
        },
        {
            "id": "5",
            "title": "Getting Started with Docker",
            "content": "Docker containers help package applications with their dependencies for consistent deployment.",
            "category": "devops",
        },
    ]

    return documents


def upload_documents(documents):
    """Upload test documents to the index"""
    print(f"\n📤 Uploading documents to '{INDEX_NAME}'...")

    documents_with_vectors = []
    for doc in documents:  # Your original document data
        # Generate the embedding for the content
        content_vector = generate_embeddings(doc["content"])

        documents_with_vectors.append(
            {
                "id": doc["id"],
                "title": doc["title"],
                "content": doc["content"],
                "category": doc["category"],
                "content_vector": content_vector,  # Add the vector to the doc
            }
        )

    # Create search client for document operations
    search_client = SearchClient(AI_SEARCH_SERVICE_ENDPOINT, INDEX_NAME, credential)

    try:
        result = search_client.upload_documents(documents=documents_with_vectors)
        uploaded_count = sum(1 for r in result if r.succeeded)
        print(
            f"✓ Uploaded {uploaded_count}/{len(documents_with_vectors)} documents successfully"
        )
        return True
    except Exception as e:
        print(f"✗ Failed to upload documents: {e}")
        return False


def search_documents(question):
    """Search for documents based on user question"""
    print(f"\n🔍 Searching for: '{question}'")
    print("-" * 60)

    # You still need to vectorize the query for the vector part
    question_vector = generate_embeddings(question)

    search_client = SearchClient(AI_SEARCH_SERVICE_ENDPOINT, INDEX_NAME, credential)

    try:
        results = search_client.search(
            search_text=question,  # <-- The keyword search part
            vector_queries=[  # <-- The vector search part
                {
                    "kind": "vector",
                    "vector": question_vector,
                    "fields": "content_vector",  # Requires a vector field in your index
                    "k": 5,
                }
            ],
            query_type="semantic",  # <-- Enable semantic reranking
            semantic_configuration_name="my_semantic_config",  # <-- The config name
            select=["title", "content", "category"],
            include_total_count=True,
        )

        # Get total count
        total_count = results.get_count()

        if total_count == 0:
            print("   No results found.\n")
            return

        print(f"   Found {total_count} result(s):\n")

        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   Category: {result['category']}")
            print(f"   Score: {result['@search.score']:.4f}")
            print(f"   Reranker Score: {result['@search.reranker_score']:.4f}")

            # Show a snippet of the content
            content = result["content"]
            snippet = content[:120] + "..." if len(content) > 120 else content
            print(f"   Preview: {snippet}\n")

        # Create a list of results to return
        results_list = []
        for result in results:
            results_list.append(
                {
                    "title": result["title"],
                    "category": result["category"],
                    "score": result[
                        "@search.score"
                    ],  # BM25 relevance score for keyword search
                    "search_rank": result[
                        "@search.reranker_score"
                    ],  # Semantic reranking score
                    "content": result["content"],
                }
            )

        return results_list

    except Exception as e:
        print(f"✗ Search failed: {e}")


# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

user_message_text = "How do I cross the road?"

print("=" * 60)
print("Azure AI Search Script")
print("=" * 60)

# Step 1: Create index
create_index()

# Step 2: Get documents to upload
documents = get_documents()

# Step 3: Upload documents
upload_documents(documents)

# Step 4: Run the search
results = search_documents(user_message_text)

# =============================================================================
# UNIT 7 SUMMARY
# =============================================================================
# This script demonstrates the end-to-end process of deploying and using Azure AI Search
# with semantic and hybrid search capabilities for the AI-103 exam:
#
# 1. Deploy an Azure AI Search service using Bicep (infrastructure-as-code).
# 2. Create a search index with a rich schema including:
#    - Traditional text fields (title, content, category) for keyword search
#    - Vector fields (content_vector) for semantic similarity search
#    - Vector search configuration using HNSW algorithm for efficient similarity matching
#    - Semantic configuration for reranking search results using language models
# 3. Generate vector embeddings for document content using Azure OpenAI's text-embedding-3-small model.
# 4. Upload and ingest documents with their corresponding embeddings into the index.
# 5. Perform hybrid search queries that combine:
#    - Keyword search (BM25 algorithm for lexical matching)
#    - Vector search (cosine similarity for semantic understanding)
#    - Semantic reranking (language model-based result reordering)
# 6. Assign RBAC roles (Search Service Contributor, Search Index Data Contributor,
#    Search Index Data Reader) using Azure CLI for secure access.
# 7. Learn that Azure AI Search enhances traditional search (tokenization, stemming, BM25 scoring)
#    with modern AI capabilities like vector embeddings and semantic reranking for superior relevance.
