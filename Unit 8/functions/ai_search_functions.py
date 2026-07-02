# =============================================================================
# AI SEARCH FUNCTIONS
# =============================================================================

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


def generate_embeddings(openai_client, embedding_model_deployment_name, text):
    """Generate a vector embedding for the given text."""
    response = openai_client.embeddings.create(
        input=text, model=embedding_model_deployment_name
    )
    embedding = response.data[0].embedding
    return embedding


def create_index(index_client, index_name):
    print(f"📋 Creating index '{index_name}'...")

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
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    # Check if the index already exists
    try:
        index_client.get_index(index_name)
        print(f"ℹ️ Index '{index_name}' already exists. Skipping creation.")
        return "Index already exists"
    except Exception:
        # If not found, create the index
        try:
            index_client.create_index(index)
            print(f"✓ Index '{index_name}' created successfully")
            return "Index created"
        except Exception as e:
            print(f"✗ Failed to create index: {e}")
            return False


def get_documents():

    documents = [
        {
            "id": "order-1",
            "title": "Order: 55-inch 4K Smart TV",
            "content": (
                "Order ID: 12345. Customer purchased a 55-inch 4K Ultra HD Smart TV, "
                "brand: Contoso Electronics, model: UltraView 5500, serial number: TV-987654321. "
                "Order date: 2024-11-15. Delivery address: 123 Main St, Sydney, NSW. "
                "The TV features HDR, built-in Wi-Fi, and voice assistant support. "
            ),
            "category": "order",
        },
        {
            "id": "order-2",
            "title": "Order: Mountain Bike",
            "content": (
                "Order ID: 54321. Customer purchased a 21-speed mountain bike, "
                "brand: AdventureCycles, model: TrailBlazer 3000. "
                "Order date: 2023-07-10. Delivery address: 456 Elm St, Melbourne, VIC. "
                "The bike features front suspension and disc brakes."
            ),
            "category": "order",
        },
        {
            "id": "order-3",
            "title": "Order: Espresso Coffee Machine",
            "content": (
                "Order ID: 67890. Customer purchased an espresso coffee machine, "
                "brand: BrewMaster, model: ProBarista X2. "
                "Order date: 2024-01-22. Delivery address: 789 Oak Ave, Brisbane, QLD. "
                "The machine includes a milk frother and digital display."
            ),
            "category": "order",
        },
        {
            "id": "order-4",
            "title": "Order: Yoga Mat",
            "content": (
                "Order ID: 24680. Customer purchased a non-slip yoga mat, "
                "brand: ZenFit, model: ComfortMat 6mm. "
                "Order date: 2022-09-05. Delivery address: 321 Maple Rd, Perth, WA. "
                "The mat is eco-friendly and lightweight."
            ),
            "category": "order",
        },
    ]

    return documents


def upload_documents(
    ai_search_client,
    openai_client,
    embedding_model_deployment_name,
    index_name,
    documents,
):
    """Upload test documents to the index"""
    print(f"\n📤 Uploading documents to '{index_name}'...")

    documents_with_vectors = []
    for doc in documents:  # Your original document data
        # Generate the embedding for the content
        content_vector = generate_embeddings(
            openai_client, embedding_model_deployment_name, doc["content"]
        )

        documents_with_vectors.append(
            {
                "id": doc["id"],
                "title": doc["title"],
                "content": doc["content"],
                "category": doc["category"],
                "content_vector": content_vector,  # Add the vector to the doc
            }
        )

    try:
        result = ai_search_client.upload_documents(documents=documents_with_vectors)
        uploaded_count = sum(1 for r in result if r.succeeded)
        print(
            f"✓ Uploaded {uploaded_count}/{len(documents_with_vectors)} documents successfully"
        )
        return True
    except Exception as e:
        print(f"✗ Failed to upload documents: {e}")
        return False


def search_documents(
    ai_search_client, openai_client, embedding_model_deployment_name, question, top_k
):
    """Search for documents based on user question"""
    print(f"\n🔍 Searching for: '{question}'")
    print("-" * 60)

    # You still need to vectorize the query for the vector part
    question_vector = generate_embeddings(
        openai_client, embedding_model_deployment_name, question
    )

    try:
        results = ai_search_client.search(
            search_text=question,  # <-- The keyword search part
            vector_queries=[  # <-- The vector search part
                {
                    "kind": "vector",
                    "vector": question_vector,
                    "fields": "content_vector",  # Requires a vector field in your index
                    "k": top_k,  # Number of results to return
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

        results_formatted = []
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   Category: {result['category']}")
            print(f"   Score: {result['@search.score']:.4f}")
            print(f"   Reranker Score: {result['@search.reranker_score']:.4f}")

            # Show a snippet of the content
            content = result["content"]
            snippet = content[:120] + "..." if len(content) > 120 else content
            print(f"   Preview: {snippet}\n")

            results_formatted.append(
                f"[{i}] (Reranker Score: {result['@search.reranker_score']:.2f}) - {result['title']}\n"
                f"Content: {result['content']}..."
            )
        results_formatted = "\n\n".join(results_formatted)
        return results_formatted

    except Exception as e:
        print(f"✗ Search failed: {e}")
