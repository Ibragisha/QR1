import math
from typing import List
from enum import Enum
from PIL import Image

class ErrorCorrectionLevel(Enum):
    """Уровни коррекции ошибок"""
    L = 0  # 7% коррекции ошибок
    M = 1  # 15% коррекции ошибок  
    Q = 2  # 25% коррекции ошибок
    H = 3  # 30% коррекции ошибок

class DataEncoder:
    """Модуль кодирования данных для QR-кодов"""
    
    def __init__(self, version: int, error_correction: ErrorCorrectionLevel):
        self.version = version
        self.error_correction = error_correction
        self.capacity = self._get_capacity()
        
    def _get_capacity(self) -> int:
        """Упрощенная таблица емкости (числовой режим)"""
        capacities = {
            (1, ErrorCorrectionLevel.L): 41,
            (1, ErrorCorrectionLevel.M): 34,
            (1, ErrorCorrectionLevel.Q): 27,
            (1, ErrorCorrectionLevel.H): 17,
            
        }
        return capacities.get((self.version, self.error_correction), 100)
    
    def encode(self, data: str) -> List[int]:
        """Кодирование данных по стандарту QR-кода"""
        # Выбор режима кодирования на основе входных данных
        if data.isdigit():
            return self._encode_numeric(data)
        else:
            return self._encode_byte(data)
    
    def _encode_numeric(self, data: str) -> List[int]:
        """Кодирование числовых данных"""
        result = []
        
        # Индикатор режима
        result.extend([0, 0, 0, 1])
        
        # Индикатор количества символов
        count_bits = self._get_character_count_bits()
        char_count = len(data)
        result.extend(self._number_to_bits(char_count, count_bits))
        
        # Кодирование числовых данных группами по 3 цифры
        i = 0
        while i < len(data):
            if i + 3 <= len(data):
                
                number = int(data[i:i+3])
                result.extend(self._number_to_bits(number, 10))
                i += 3
            elif i + 2 <= len(data):
                
                number = int(data[i:i+2])
                result.extend(self._number_to_bits(number, 7))
                i += 2
            else:
                
                number = int(data[i])
                result.extend(self._number_to_bits(number, 4))
                i += 1
        
        
        result.extend([0, 0, 0, 0])
        
        
        while len(result) < self.capacity:
            result.extend([1, 1, 1, 0, 1, 1, 0, 0])  
    
        return result[:self.capacity]
    
    def _encode_byte(self, data: str) -> List[int]:
        
        result = []
        
        # Индикатор режима (0100 для байтового режима)
        result.extend([0, 1, 0, 0])
        
        # Индикатор количества символов
        count_bits = self._get_character_count_bits()
        char_count = len(data.encode('utf-8'))
        result.extend(self._number_to_bits(char_count, count_bits))
        
        # Кодирование каждого байта
        for byte in data.encode('utf-8'):
            result.extend(self._number_to_bits(byte, 8))
        
        # Добавление терминатора
        result.extend([0, 0, 0, 0])
        
        # Добавление заполнения
        while len(result) < self.capacity:
            result.extend([1, 1, 1, 0, 1, 1, 0, 0])
        
        return result[:self.capacity]
    
    def _get_character_count_bits(self) -> int:
        
        if 1 <= self.version <= 9:
            return 10 if self.error_correction in [ErrorCorrectionLevel.L, ErrorCorrectionLevel.M] else 8
        else:
            return 12
    
    def _number_to_bits(self, number: int, bit_length: int) -> List[int]:
        
        return [int(bit) for bit in format(number, f'0{bit_length}b')]

class ReedSolomon:
    
    
    def encode(self, data: List[int], version: int, error_correction: ErrorCorrectionLevel) -> List[int]:
        
        return data + data[:10]  # Простая избыточность

class MatrixConstructor:
    """Построитель матрицы QR-кода"""
    
    def __init__(self, version: int):
        self.version = version
        self.size = (version - 1) * 4 + 21
        self.matrix = [[False] * self.size for _ in range(self.size)]
    
    def build_matrix(self, data: List[int]) -> List[List[bool]]:
        """Построение полной матрицы QR-кода"""
        self._add_finder_patterns()
        self._add_alignment_patterns()
        self._add_timing_patterns()
        self._add_dark_module()
        self._add_format_info()
        self._add_data(data)
        self._apply_mask()
        
        return self.matrix
    
    def _add_finder_patterns(self):
        
        patterns_pos = [ 
            (0, 0),  
            (self.size - 7, 0),
            (0, self.size - 7)   
        ]
        
        for x, y in patterns_pos:
            
            for i in range(7):
                for j in range(7):
                    if i == 0 or i == 6 or j == 0 or j == 6:
                        self.matrix[y + j][x + i] = True
                    elif 2 <= i <= 4 and 2 <= j <= 4:
                        self.matrix[y + j][x + i] = True
                    else:
                        self.matrix[y + j][x + i] = False
    
    def _add_alignment_patterns(self):
        
        if self.version == 1:
            return
        
        
        positions = self._get_alignment_positions()
        
        for x, y in positions:
            
            if (x < 9 and y < 9) or (x > self.size - 10 and y < 9) or (x < 9 and y > self.size - 10):
                continue
            
            
            for i in range(5):
                for j in range(5):
                    if i == 0 or i == 4 or j == 0 or j == 4:
                        self.matrix[y + j - 2][x + i - 2] = True
                    elif i == 2 and j == 2:
                        self.matrix[y + j - 2][x + i - 2] = True
                    else:
                        self.matrix[y + j - 2][x + i - 2] = False
    
    def _get_alignment_positions(self) -> List[tuple]:
        
        if 2 <= self.version <= 6:
            return [(self.size - 7, self.size - 7)]
        else:
            
            return [(self.size - 9, self.size - 9)]
    
    def _add_timing_patterns(self):
    
        for i in range(8, self.size - 8):
            self.matrix[6][i] = (i % 2 == 0)
        
        
        for i in range(8, self.size - 8):
            self.matrix[i][6] = (i % 2 == 0)
    
    def _add_dark_module(self):
        
        self.matrix[4 * self.version + 9][8] = True
    
    def _add_format_info(self):
    
        # Упрощенная информация о формате 
        format_info = [False] * 15
        
        for i in range(15):
            if i < 8:
                self.matrix[8][i if i != 6 else 7] = format_info[i]
            else:
                self.matrix[14 - i][8] = format_info[i]
    
    def _add_data(self, data: List[int]):
        # Упрощенное размещение данных 
        bit_index = 0
        for y in range(self.size):
            for x in range(self.size):
                if not self._is_function_pattern(x, y) and bit_index < len(data):
                    self.matrix[y][x] = bool(data[bit_index])
                    bit_index += 1
    
    def _is_function_pattern(self, x: int, y: int) -> bool:
        # Паттерны поиска
        if (x < 7 and y < 7) or (x > self.size - 8 and y < 7) or (x < 7 and y > self.size - 8):
            return True
        
        # Тайминг-паттерны
        if x == 6 or y == 6:
            return True
        
        # Область информации о формате
        if (x < 9 and y < 9) or (x > self.size - 9 and y < 9) or (x < 9 and y > self.size - 9):
            return True
        
        return False
    
    def _apply_mask(self):

        for y in range(self.size):
            for x in range(self.size):
                if not self._is_function_pattern(x, y):
                    if (x + y) % 3 == 0:  
                        self.matrix[y][x] = not self.matrix[y][x]

class QRCode:
    
    def __init__(self, version: int = 1, error_correction: ErrorCorrectionLevel = ErrorCorrectionLevel.M):

        self.version = version
        self.error_correction = error_correction
        self.size = self._calculate_size()
        
        # Инициализация компонентов
        self.encoder = DataEncoder(version, error_correction)
        self.error_corrector = ReedSolomon()
        self.matrix_constructor = MatrixConstructor(version)
        
    def _calculate_size(self) -> int:
        """Вычисление размера матрицы на основе версии"""
        return (self.version - 1) * 4 + 21
    
    def generate(self, data: str) -> List[List[bool]]:
    
        # Шаг 1: Кодирование данных
        encoded_data = self.encoder.encode(data)
        
        # Шаг 2: Кодирование коррекции ошибок
        error_corrected_data = self.error_corrector.encode(
            encoded_data, 
            self.version, 
            self.error_correction
        )
        
        # Шаг 3: Построение матрицы
        qr_matrix = self.matrix_constructor.build_matrix(error_corrected_data)
        
        return qr_matrix
    
    def save_as_image(self, data: str, filename: str, scale: int = 10):
      
        try:
            matrix = self.generate(data)
            size = len(matrix)
            
            # Создание изображения
            img_size = size * scale
            img = Image.new('RGB', (img_size, img_size), 'white')
            pixels = img.load()
            
            # Отрисовка QR-кода
            for y in range(size):
                for x in range(size):
                    color = (0, 0, 0) if matrix[y][x] else (255, 255, 255)
                    for dy in range(scale):
                        for dx in range(scale):
                            pixels[x * scale + dx, y * scale + dy] = color
            
            img.save(filename)
            print(f"QR-код сохранен как {filename}")
            
        except ImportError:
            print("PIL/Pillow не доступен. Установите: pip install pillow")
    
    def print_ascii(self, data: str):
        """
        Вывод QR-кода
        """
        matrix = self.generate(data)
        size = len(matrix)
        
        for y in range(size):
            line = ""
            for x in range(size):
                line += "██" if matrix[y][x] else "  "
            print(line)

def main():
    print("QR Code Generator Library Demo")
    print("=" * 40)
    
    # Пример 1: Простой QR-код
    print("\n1. Generating simple QR code...")
    qr = QRCode(version=1, error_correction=ErrorCorrectionLevel.M)
    qr.print_ascii("HELLO QR")
    
    # Пример 2: QR-код с высокой коррекцией ошибок
    print("\n2. Generating QR code with high error correction...")
    qr_high = QRCode(version=2, error_correction=ErrorCorrectionLevel.H)
    qr_high.print_ascii("ERROR CORRECTION TEST")
    
    # Пример 3: Сохранение как изображение
    print("\n3. Saving QR code as image...")
    try:
        qr_image = QRCode(version=3, error_correction=ErrorCorrectionLevel.Q)
        qr_image.save_as_image("https://github.com", "github_qr.png", scale=5)
        print("Изображение сохранено как 'github_qr.png'")
    except Exception as e:
        print(f"Ошибка сохранения изображения: {e}")
    
    # Пример 4: Разные типы данных
    print("\n4. Testing different data types...")
    test_data = [
        "1234567890",  # Числовые
        "Hello World!",  # Буквенно-цифровые
        "https://example.com",  # URL
    ]
    
    for i, data in enumerate(test_data, 1):
        print(f"\nData {i}: {data}")
        test_qr = QRCode(version=1, error_correction=ErrorCorrectionLevel.L)
        test_qr.print_ascii(data[:20])  # Ограничение для отображения

if __name__ == "__main__":
    main()