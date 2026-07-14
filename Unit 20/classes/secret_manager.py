from functools import lru_cache

class SecretManager:
    """
    Quản lý việc lấy thông tin bí mật (secret) một cách an toàn
    từ Azure Key Vault.

    Lớp này sử dụng hai lớp bộ nhớ đệm để giảm số lần gọi mạng
    đến Azure Key Vault:

    1. `lru_cache`: lưu kết quả trả về của phương thức `get_secret`.
    2. `_cache`: bộ nhớ đệm dạng dictionary được quản lý thủ công.

    Việc dùng bộ nhớ đệm giúp tăng tốc độ truy xuất và giảm chi phí
    cũng như số lượng yêu cầu gửi đến Key Vault.
    """

    def __init__(self, secret_client):
        """
        Khởi tạo đối tượng quản lý secret.
        
        secret_client:
            Azure Key Vault SecretClient đã được khởi tạo trước đó,
            thường sử dụng Managed Identity hoặc DefaultAzureCredential.
        """
        self.secret_client = secret_client

        # Bộ nhớ đệm: Key là tên secret, value là giá trị của secret.
        self._cache = {}

    @lru_cache(maxsize=128)
    def get_secret(self, secret_name: str) -> str:
        """
        Lấy giá trị của một secret từ Azure Key Vault và lưu vào bộ nhớ đệm.

        Thứ tự xử lý:

        1. Kiểm tra bộ nhớ đệm nội bộ `_cache`.
        2. Nếu chưa có, gọi Azure Key Vault để lấy secret.
        3. Lưu giá trị secret vào `_cache`.
        4. Trả về giá trị secret dưới dạng chuỗi.

        Ngoài `_cache`, decorator `lru_cache` cũng lưu kết quả của phương thức
        này. Vì vậy, các lần gọi tiếp theo với cùng `secret_name` thường sẽ
        không cần thực thi lại nội dung phương thức.

        Trong đoạn code hiện tại, hai cache gần như trùng chức năng. Sau lần gọi đầu tiên, cả hai đều chứa cùng một giá trị. 
        Trong điều kiện sử dụng bình thường, _cache hầu như không mang lại lợi ích vì lru_cache đã trả kết quả trước khi _cache được kiểm tra.
        _cache phát huy tác dụng trong một số tình huống, chẳng hạn một mục đã bị lru_cache loại bỏ do vượt quá 128 mục nhưng vẫn còn trong _cache.

        secret_name: Tên của secret cần lấy trong Azure Key Vault.

        Return: giá trị của secret dưới dạng chuỗi.

        Exception:
            Trả về ngoại lệ nếu không thể lấy secret, như không đủ quyền truy cập, 
            secret không tồn tại hoặc xảy ra lỗi kết nối đến Azure Key Vault.
        """
        try:
            # Kiểm tra bộ nhớ đệm trước để tránh gọi đến Key Vault.
            if secret_name in self._cache:
                return self._cache[secret_name]

            # Nếu chưa có trong bộ nhớ đệm, lấy secret từ Azure Key Vault.
            secret = self.get_secret_without_caching(secret_name)

            # Azure Key Vault trả về một đối tượng secret.
            # Thuộc tính `.value` chứa giá trị thực tế của secret.
            self._cache[secret_name] = secret.value

            return secret.value

        except Exception as e:
            # Ghi lại lỗi để hỗ trợ kiểm tra và xử lý sự cố.
            # Không nên ghi trực tiếp giá trị của secret vào log.
            print(f"ERROR: Failed to retrieve secret '{secret_name}': {e}")
            raise

    def get_secret_without_caching(self, secret_name: str) -> str:
        """
        Lấy secret trực tiếp từ Azure Key Vault mà không kiểm tra `_cache`.

        Phương thức này được dùng bên trong `get_secret` khi secret chưa có
        trong bộ nhớ đệm.

        Lưu ý: Phương thức này bỏ qua `_cache` và `lru_cache`, nhưng lời gọi
        trực tiếp tới nó vẫn gửi yêu cầu mạng đến Azure Key Vault.

        secret_name: Tên của secret cần lấy.

        Return: Đối tượng secret do Azure Key Vault SDK trả về.
        Giá trị thực tế của secret có thể được lấy thông qua `secret.value`.
        """
        secret = self.secret_client.get_secret(secret_name)
        return secret

    def clear_cache(self):
        """
        Xóa toàn bộ dữ liệu secret đang được lưu trong bộ nhớ đệm.

        Cần xóa cả hai lớp cache:

        1. `_cache`: dictionary được quản lý thủ công.
        2. Cache của decorator `lru_cache`.

        Nên gọi phương thức này khi secret trên Azure Key Vault đã được
        cập nhật hoặc xoay vòng và ứng dụng cần lấy giá trị mới.
        """
        # Xóa bộ nhớ đệm.
        self._cache.clear()

        # Xóa các kết quả đang được decorator `lru_cache` lưu giữ.
        self.get_secret.cache_clear()
