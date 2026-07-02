"""
UNIT 6: Azure AI Search (Part 1) - Indexing and Querying, without Vector Search or Semantic Search.

NEW IN THIS UNIT:
1. Deploy a basic Azure AI Search service using Bicep, an infrastructure-as-code language that enables automated, repeatable deployments in Azure.
2. Design and create a search index, defining the structure and searchable fields for your data.
3. Upload and ingest documents into the index, preparing your data for search and retrieval.
4. Perform search queries to retrieve relevant documents, learning how to use the Azure AI Search API for real-world information discovery scenarios.
5. Assign role-based access control (RBAC) roles to users for the Azure AI Search resource, including:
    - Search Service Contributor
    - Search Index Data Contributor
    - Search Index Data Reader
    You will learn how to use the Azure CLI to grant these roles, enabling secure and appropriate access to search resources and data.

By completing these steps, you will gain hands-on experience with the full lifecycle of Azure AI Search: provisioning resources, modeling data, loading content, and building intelligent search solutions for enterprise applications.
"""

import os

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SimpleField,
    SearchableField,
    SearchIndex,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

AI_SEARCH_SERVICE_ENDPOINT = os.getenv("AI_SEARCH_SERVICE_ENDPOINT")

INDEX_NAME = "unit_6_ai_search_index"

# =============================================================================
# AUTHENTICATION
# =============================================================================

credential = DefaultAzureCredential()

# =============================================================================
# AI SEARCH FUNCTIONS
# =============================================================================


def create_index():
    """
    Creates a simple Azure AI Search index with a basic schema.

    How it works:
    - Defines an index schema with fields: 'id' (key), 'title', 'content', and 'category'.
    - Uses Azure SDK's SearchIndex and field types (SimpleField, SearchableField) to specify data types and search/filter capabilities.
    - Connects to your Azure AI Search service using the endpoint and DefaultAzureCredential for authentication.
    - Calls the Azure SearchIndexClient to create the index in your Azure AI Search resource.

    Azure AI Search connection:
    - This function creates the index in your Azure AI Search service, which is a cloud-based search solution for indexing, querying, and retrieving documents.
    - The index schema determines how your data is stored and what fields can be searched, filtered, or retrieved.

    Vector embeddings support:
    - This example schema does NOT include a vector field, so it cannot be used for vector search or semantic search with embeddings.
    - To enable vector search (for semantic or hybrid search), you must add a field of type 'Collection(Edm.Single)' or 'Edm.Single' (for float vectors) and configure it for vector search in the index definition.
    - See Azure AI Search documentation for details on adding vector fields and configuring vector search: https://learn.microsoft.com/azure/search/vector-search-overview

    Returns True if the index is created successfully, otherwise False.
    """
    print(f"📋 Creating index '{INDEX_NAME}'...")

    # Define the index schema
    fields = [
        SimpleField(name="id", type="Edm.String", key=True),
        SearchableField(name="title", type="Edm.String"),
        SearchableField(name="content", type="Edm.String"),
        SimpleField(name="category", type="Edm.String", filterable=True),
    ]
    index = SearchIndex(name=INDEX_NAME, fields=fields)

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


def upload_documents():
    """Upload test documents to the index"""
    print(f"\n📤 Uploading documents to '{INDEX_NAME}'...")

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

    # Create search client for document operations
    search_client = SearchClient(AI_SEARCH_SERVICE_ENDPOINT, INDEX_NAME, credential)

    try:
        result = search_client.upload_documents(documents=documents)
        uploaded_count = sum(1 for r in result if r.succeeded)
        print(f"✓ Uploaded {uploaded_count}/{len(documents)} documents successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to upload documents: {e}")
        return False


def search_documents(question):
    """Search for documents based on user question"""
    print(f"\n🔍 Searching for: '{question}'")
    print("-" * 60)

    search_client = SearchClient(AI_SEARCH_SERVICE_ENDPOINT, INDEX_NAME, credential)

    try:
        # Perform the search
        results = search_client.search(
            search_text=question,
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

            # Show a snippet of the content
            content = result["content"]
            snippet = content[:120] + "..." if len(content) > 120 else content
            print(f"   Preview: {snippet}\n")

        return results

    except Exception as e:
        print(f"✗ Search failed: {e}")


# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

user_message_text = "What is Docker?"

print("=" * 60)
print("Azure AI Search Script")
print("=" * 60)

# Step 1: Create index
create_index()

# Step 2: Upload documents
upload_documents()

# Step 3: Run the search
results = search_documents(user_message_text)

print()

# =============================================================================
# UNIT 6 SUMMARY
# =============================================================================
# This script demonstrates the end-to-end process of deploying and using Azure AI Search for the AI-103 exam:
# 1. Deploy an Azure AI Search service using Bicep (infrastructure-as-code).
# 2. Create a search index and define its schema.
# 3. Upload and ingest documents into the index.
# 4. Perform search queries to retrieve relevant documents.
# 5. Assign RBAC roles (Search Service Contributor, Search Index Data Contributor, Search Index Data Reader) using Azure CLI for secure access.
# 6. You learned that it Azure AI Search uses tokenization, stemming, and scoring algorithms (like BM25) to rank results by relevance.
#
# Key exam takeaways:
# - Understand the lifecycle of Azure AI Search: deployment, indexing, data ingestion, and querying.
# - Use Bicep for repeatable, automated resource provisioning.
# - Design effective index schemas for search scenarios.
# - Upload and manage searchable content programmatically.
# - Apply RBAC for secure, role-based access to search resources and data.
