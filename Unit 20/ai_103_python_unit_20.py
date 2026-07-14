"""
UNIT 20: Tích hợp Agent hoàn chỉnh – Hệ thống sẵn sàng triển khai

ĐIỂM MỚI TRONG UNIT NÀY:
1. Azure Key Vault — Lưu trữ an toàn secret, key và certificate; dùng Managed Identity để tránh ghi cứng thông tin xác thực.
2. Content Safety — Kiểm tra độ an toàn của nội dung đầu vào và đầu ra.
3. Azure AI đa phương thức — Tích hợp Vision, Speech, Document Intelligence, Text Analytics và Azure OpenAI; hỗ trợ nhiều model endpoint.
4. Tiền xử lý NLP — Chuẩn hóa văn bản qua tách từ, chuẩn hóa và xử lý stopword.
5. Bộ nhớ dài hạn Cosmos DB — Tải và lưu hồ sơ người dùng để agent trả lời theo ngữ cảnh.
6. Cập nhật bộ nhớ bằng SLM — Dùng model nhỏ để cập nhật bộ nhớ dài hạn sau mỗi cuộc hội thoại.
7. Redis ở chế độ cache cục bộ — Có cơ chế dự phòng khi không kết nối Redis bên ngoài.
8. Vòng lặp hội thoại — Hỗ trợ tương tác nhiều lượt liên tục.
9. Manager Agent và agent hỗ trợ — Điều phối tác vụ và tích hợp dịch vụ bên ngoài.
10. MCP Server — Cho phép agent gọi công cụ bên ngoài qua URL và API key cấu hình trong biến môi trường hoặc `config.yaml`.
"""

import os
import yaml

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.vision.imageanalysis import ImageAnalysisClient
import azure.cognitiveservices.speech as speechsdk
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.keyvault.secrets import SecretClient
from azure.cosmos import CosmosClient

from functions.helper_functions import count_tokens
from classes.content_safety import ContentSafety
from classes.azure_ai_services import AzureAIService
from classes.azure_nlp_services import AzureNLPService
from classes.secret_manager import SecretManager
from classes.cosmos_memory import CosmosMemory
from classes.redis_memory import RedisMemory
from classes.refund_agent import RefundAgent
from classes.product_agent import ProductAgent
from classes.manager_agent import ManagerAgent
from classes.user_preferences_agent import UserPreferencesAgent

# =============================================================================
# CẤU HÌNH
# =============================================================================

key_vault_url = os.getenv("KEY_VAULT_URL")
user_name = os.getenv("USER_NAME")
user_role = os.getenv("USER_ROLE")
region = os.getenv("REGION")
mcp_server_url = os.getenv("MCP_SERVER_URL")
mcp_api_key = os.getenv("MCP_API_KEY")

with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# =============================================================================
# XÁC THỰC VÀ KHỞI TẠO CLIENT
# =============================================================================

credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
secret_manager = SecretManager(secret_client)

# Tạo các client Azure bằng thông tin lấy từ Key Vault.
token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
openai_client = OpenAI(
    base_url=secret_manager.get_secret("AZURE-OPENAI-ENDPOINT"), api_key=token_provider
)
content_safety_client = ContentSafetyClient(
    endpoint=secret_manager.get_secret("CONTENT-SAFETY-ENDPOINT"), credential=credential
)
vision_client = ImageAnalysisClient(
    endpoint=secret_manager.get_secret("VISION-ENDPOINT"),
    credential=AzureKeyCredential(secret_manager.get_secret("VISION-KEY")),
)
speech_config_client = speechsdk.SpeechConfig(
    subscription=secret_manager.get_secret("SPEECH-KEY"), region=region
)
doc_intel_client = DocumentIntelligenceClient(
    endpoint=secret_manager.get_secret("DOC-INTEL-ENDPOINT"),
    credential=AzureKeyCredential(secret_manager.get_secret("DOC-INTEL-KEY")),
)
language_client = TextAnalyticsClient(
    endpoint=secret_manager.get_secret("LANGUAGE-ENDPOINT"),
    credential=AzureKeyCredential(secret_manager.get_secret("LANGUAGE-KEY")),
)
cosmos_db_client = CosmosClient(
    url=secret_manager.get_secret("COSMOSDB-ENDPOINT"),
    credential=secret_manager.get_secret("COSMOSDB-PRIMARY-KEY"),
)
database_client = cosmos_db_client.get_database_client(
    secret_manager.get_secret("COSMOSDB-DATABASE-NAME")
)
if database_client.read():
    print("Successfully connected to Cosmos DB database")
container_client = database_client.get_container_client(
    secret_manager.get_secret("COSMOSDB-CONTAINER-NAME")
)
if container_client.read():
    print("Successfully connected to Cosmos DB container")

# =============================================================================
# KHỞI TẠO CÁC THÀNH PHẦN
# =============================================================================

# Kiểm tra an toàn nội dung.
content_safety = ContentSafety(content_safety_client, config)

# Xử lý dữ liệu đa phương thức từ các dịch vụ Azure AI.
azure_ai_service = AzureAIService(
    vision_client=vision_client,
    speech_config=speech_config_client,
    doc_intel_client=doc_intel_client,
)

# Tiền xử lý và phân tích văn bản.
azure_nlp_service = AzureNLPService(language_client=language_client, config=config)

# Lưu và đọc bộ nhớ dài hạn từ Cosmos DB.
cosmos_memory = CosmosMemory(
    cosmos_client=cosmos_db_client,
    database_client=database_client,
    container_client=container_client,
    config=config,
)

# Dùng cache cục bộ vì unit này không kết nối Redis thật.
redis_memory = RedisMemory(redis_client=None, config=config)

# Xử lý yêu cầu hoàn tiền.
refund_agent = RefundAgent(
    openai_client=openai_client,
    model_deployment_name=secret_manager.get_secret("LLM-MODEL-DEPLOYMENT-NAME"),
    redis_memory=redis_memory,
    user_name=user_name,
    user_role=user_role,
    config=config,
)

# Xử lý yêu cầu liên quan đến sản phẩm và MCP Server.
product_agent = ProductAgent(
    openai_client=openai_client,
    model_deployment_name=secret_manager.get_secret("LLM-MODEL-DEPLOYMENT-NAME"),
    redis_memory=redis_memory,
    user_name=user_name,
    user_role=user_role,
    mcp_server_url=mcp_server_url,
    mcp_api_key=mcp_api_key,
    config=config,
)

# Điều phối yêu cầu đến agent phù hợp.
manager_agent = ManagerAgent(
    openai_client=openai_client,
    model_deployment_name=secret_manager.get_secret("LLM-MODEL-DEPLOYMENT-NAME"),
    refund_agent=refund_agent,
    product_agent=product_agent,
    user_name=user_name,
    user_role=user_role,
    config=config,
)

# Trích xuất và cập nhật sở thích người dùng.
user_preferences_agent = UserPreferencesAgent(
    openai_client=openai_client,
    model_deployment_name=secret_manager.get_secret("SLM-MODEL-DEPLOYMENT-NAME"),
    redis_memory=redis_memory,
    config=config,
)

# =============================================================================
# LUỒNG XỬ LÝ CHÍNH
# =============================================================================

# Thực tế nên tạo ID riêng cho mỗi phiên người dùng.
session_id = "session_12346"


def interactive_loop():
    print("Interactive mode started. Type 'exit' or 'quit' to stop.")
    message_count = 0
    while True:
        try:
            user_message_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting interactive mode.")
            break

        if not user_message_text:
            continue
        if user_message_text.lower() in ("exit", "quit"):
            print("Exiting interactive mode.")
            break

        # Kiểm tra an toàn đầu vào.
        print("\n[INPUT FILTER] Scanning user message...")
        if not content_safety.is_text_safe(user_message_text):
            print("User message blocked by Content Safety.")
            continue
        print("User message passed safety check.")

        # Chỉ gửi ảnh mẫu ở tin nhắn đầu tiên.
        if message_count == 0:
            print(
                "\n[AZURE NLP SERVICE] Preprocessing user input with Azure AI Language (multimodal)..."
            )
            azure_ai_service_response = azure_ai_service.route_multimodal_request(
                content_type="jpeg", content_path="inputs/broken_tv.jpeg"
            )
            print(f"\nAzure AI Service response: {azure_ai_service_response}")
        else:
            azure_ai_service_response = None

        azure_nlp_service_response = azure_nlp_service.preprocess_user_input(
            user_message_text
        )

        # Dùng bản đã che dữ liệu nhạy cảm và gắn nhãn cho agent.
        user_message_for_agent = azure_nlp_service_response.get(
            "tagged", user_message_text
        )
        print(
            f"Preprocessed user message (with sensitive info redacted and entities tagged): {user_message_for_agent}"
        )

        # Lấy sở thích người dùng từ bộ nhớ dài hạn.
        print("\n[LONG-TERM MEMORY] Retrieving user preferences from Cosmos DB...")
        user_preferences = cosmos_memory.get_user_or_default_profile(user_id=user_name)
        print(f"\nUser preferences: {user_preferences}")

        # Manager Agent điều phối và xử lý yêu cầu.
        print("\n[MANAGER AGENT] Processing message with agent...")
        reply = manager_agent.process_message(
            user_message=user_message_for_agent,
            user_preferences=user_preferences,
            azure_ai_service_response=azure_ai_service_response,
            azure_nlp_service_response=azure_nlp_service_response,
            session_id=session_id,
        )

        # Bỏ qua lượt hiện tại nếu model không trả về kết quả.
        if reply is None:
            print("ERROR: Failed to get response from model.")
            continue

        # Kiểm tra an toàn đầu ra.
        print("\n[OUTPUT FILTER] Scanning assistant response...")
        if not content_safety.is_text_safe(reply):
            print("Assistant response blocked by Content Safety.")
            print(f"Returning safe default message: '{config['safe_responce']}'")
            print("\n" + "=" * 50)
            print("ASSISTANT REPLY (SAFE DEFAULT):")
            print("=" * 50)
            print(config["safe_responce"])
            print("=" * 50)
        else:
            print("Assistant response passed safety check.")
            print("\n" + "=" * 50)
            print("ASSISTANT REPLY:")
            print("=" * 50)
            print(reply)
            print("=" * 50)

        message_count += 1

    # Trích xuất sở thích mới từ lịch sử hội thoại.
    print(
        "\n[USER PREFERENCES AGENT] Processing conversation history to extract user preferences..."
    )
    user_preferences_reply = user_preferences_agent.process_message(
        current_preferences=user_preferences,
        session_id=session_id,
    )
    print(f"\nUser Preferences Agent reply: {user_preferences_reply}")

    # Lưu sở thích đã cập nhật vào Cosmos DB.
    print("\n[LONG-TERM MEMORY] Saving updated user preferences to Cosmos DB...")
    cosmos_memory.save_user_profile(
        user_id=user_name, preferences=user_preferences_reply
    )
    print("\nUser preferences updated in Cosmos DB.")


if __name__ == "__main__":
    interactive_loop()

# =============================================================================
# TỔNG KẾT UNIT 20
# =============================================================================
# Unit này xây dựng hệ thống agent an toàn, đa phương thức và sẵn sàng triển khai.
# Hệ thống có bộ nhớ dài hạn, kiểm tra nội dung, cache và công cụ bên ngoài.

# 1. Azure Key Vault — Quản lý secret an toàn bằng Managed Identity.
# 2. Content Safety — Kiểm tra nội dung đầu vào và đầu ra.
# 3. Azure AI đa phương thức — Kết hợp Vision, Speech, Document Intelligence, Text Analytics và Azure OpenAI.
# 4. Tiền xử lý NLP — Chuẩn hóa văn bản trước khi gửi cho agent.
# 5. Cosmos DB — Lưu hồ sơ và sở thích người dùng dài hạn.
# 6. SLM — Cập nhật bộ nhớ dài hạn sau cuộc hội thoại.
# 7. Redis — Dùng cache cục bộ khi không có kết nối Redis.
# 8. Vòng lặp hội thoại — Hỗ trợ tương tác nhiều lượt.
# 9. Hệ thống agent — Manager Agent điều phối các agent chuyên trách.
# 10. MCP Server — Kết nối agent với công cụ và dịch vụ bên ngoài.
