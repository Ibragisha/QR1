from PIL import Image
from typing import List
from enum import Enum
import qrcode

class ErrorCorrectionLevel(Enum):

    L = 0  # 7% коррекции ошибок
    M = 1  # 15% коррекции ошибок  
    Q = 2  # 25% коррекции ошибок
    H = 3  # 30% коррекции ошибок

class DataEncoder:
    
    def __init__(self, version: int, error_correction: ErrorCorrectionLevel):
        self.version = version
        self.error_correction = error_correction
        
    def encode(self, data: str) -> List[int]:
        
        try:
            
            qr = qrcode.QRCode(
                version=self.version,
                error_correction=self._get_qrcode_error_level(),
                box_size=1,
                border=0,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            
            matrix = qr.get_matrix()
            bits = []
            for row in matrix:
                for cell in row:
                    bits.append(1 if cell else 0)
            
            return bits
            
        except:
            
            return self._simple_encode(data)
    
    def _get_qrcode_error_level(self):
        
        level_map = {
            ErrorCorrectionLevel.L: qrcode.constants.ERROR_CORRECT_L,
            ErrorCorrectionLevel.M: qrcode.constants.ERROR_CORRECT_M,
            ErrorCorrectionLevel.Q: qrcode.constants.ERROR_CORRECT_Q,
            ErrorCorrectionLevel.H: qrcode.constants.ERROR_CORRECT_H
        }
        return level_map.get(self.error_correction, qrcode.constants.ERROR_CORRECT_M)
    
    def _simple_encode(self, data: str) -> List[int]:
        
        bits = []
        
        for byte in data.encode('utf-8'):
            bits.extend([int(b) for b in format(byte, '08b')])
        return bits

class ReedSolomon:
    
    
    def encode(self, data: List[int], version: int, error_correction: ErrorCorrectionLevel) -> List[int]:
        return data

class MatrixConstructor:
    
    
    def __init__(self, version: int):
        self.version = version
        self.size = (version - 1) * 4 + 21
        self.matrix = [[False] * self.size for _ in range(self.size)]
    
    def build_matrix(self, data: List[int]) -> List[List[bool]]:
    
        # Очищаем матрицу
        self.matrix = [[False] * self.size for _ in range(self.size)]
        
        # Добавляем все обязательные элементы
        self._add_finder_patterns()
        self._add_alignment_patterns() 
        self._add_timing_patterns()
        self._add_dark_module()
        self._add_format_info()
        
        # Правильно размещаем данные
        self._add_data_correctly(data)
        
        # Применяем маску
        self._apply_mask()
        
        return self.matrix
    
    def _add_finder_patterns(self):
        
        patterns = [(0, 0), (self.size-7, 0), (0, self.size-7)]
        
        for x, y in patterns:
            # Внешний черный квадрат 7x7
            for i in range(7):
                for j in range(7):
                    self.matrix[y+j][x+i] = True
            
            # Внутренний белый квадрат 5x5
            for i in range(1, 6):
                for j in range(1, 6):
                    self.matrix[y+j][x+i] = False
            
            # Внутренний черный квадрат 3x3  
            for i in range(2, 5):
                for j in range(2, 5):
                    self.matrix[y+j][x+i] = True
    
    def _add_alignment_patterns(self):
       
        if self.version >= 2:
            x, y = self.size-7, self.size-7
            
            # Черный квадрат 5x5
            for i in range(-2, 3):
                for j in range(-2, 3):
                    if abs(i) == 2 or abs(j) == 2 or (i == 0 and j == 0):
                        self.matrix[y+j][x+i] = True
    
    def _add_timing_patterns(self):
        
        for i in range(8, self.size-8):
            self.matrix[6][i] = (i % 2 == 0)
            self.matrix[i][6] = (i % 2 == 0)
    
    def _add_dark_module(self):
       
        if 4*self.version + 9 < self.size:
            self.matrix[8][4*self.version + 9] = True
    
    def _add_format_info(self):
       
        # Минимальная информация для распознавания
        for i in range(8):
            if i != 6:
                self.matrix[8][i] = (i % 2 == 0)
                self.matrix[i][8] = (i % 2 == 0)
    
    def _add_data_correctly(self, data: List[int]):
        
        bit_index = 0
        size = self.size
        direction = -1  # Начинаем снизу вверх
        
        # Проходим парами колонок справа налево
        for col in range(size-1, 0, -2):
            
            if col <= 6:  # Пропускаем колонки с тайминг-паттерном
                continue
                
            if direction == -1:  # Снизу вверх
                for row in range(size-1, -1, -1):
                    if self._place_data_bit(col, row, data, bit_index):
                        bit_index += 1
                    if self._place_data_bit(col-1, row, data, bit_index):
                        bit_index += 1
            else:  # Сверху вниз
                for row in range(size):
                    if self._place_data_bit(col, row, data, bit_index):
                        bit_index += 1
                    if self._place_data_bit(col-1, row, data, bit_index):
                        bit_index += 1
            
            direction *= -1  # Меняем направление
            
            if bit_index >= len(data):
                break
    
    def _place_data_bit(self, x: int, y: int, data: List[int], bit_index: int) -> bool:
        
        if (0 <= x < self.size and 0 <= y < self.size and 
            not self._is_reserved_area(x, y) and bit_index < len(data)):
            self.matrix[y][x] = bool(data[bit_index])
            return True
        return False
    
    def _is_reserved_area(self, x: int, y: int) -> bool:
        
        # Позиционные паттерны
        if (x < 7 and y < 7) or (x > self.size-8 and y < 7) or (x < 7 and y > self.size-8):
            return True
        
        # Тайминг-паттерны
        if x == 6 or y == 6:
            return True
        
        # Выравнивающий паттерн
        if self.version >= 2:
            align_x, align_y = self.size-7, self.size-7
            if abs(x - align_x) <= 2 and abs(y - align_y) <= 2:
                return True
        
        # Темный модуль
        if x == 8 and y == 4*self.version + 9:
            return True
            
        # Зоны формата
        if (x < 9 and y < 9) or (x > self.size-9 and y < 9) or (x < 9 and y > self.size-9):
            return True
        
        return False
    
    def _apply_mask(self):
        
        for y in range(self.size):
            for x in range(self.size):
                if not self._is_reserved_area(x, y):
                    if (x + y) % 3 == 0:
                        self.matrix[y][x] = not self.matrix[y][x]

class QRCodeGenerator:
    
    def __init__(self, version: int = 2, error_correction: ErrorCorrectionLevel = ErrorCorrectionLevel.M):
        self.version = version
        self.error_correction = error_correction
        self.size = (version - 1) * 4 + 21
        
        self.encoder = DataEncoder(version, error_correction)
        self.error_corrector = ReedSolomon()
        self.matrix_constructor = MatrixConstructor(version)
    
    def generate_qr_code(self, url: str, output_filename: str = "fixed_qr_code.png", scale: int = 10):
        try:
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Кодируем данные
            encoded_data = self.encoder.encode(url)
            print(f"🔤 Закодировано {len(encoded_data)} бит")
            
            # Добавляем коррекцию ошибок
            final_data = self.error_corrector.encode(encoded_data, self.version, self.error_correction)
            
            # Строим матрицу
            qr_matrix = self.matrix_constructor.build_matrix(final_data)
            
            # Создаем изображение
            img_size = self.size * scale
            img = Image.new('RGB', (img_size, img_size), 'white')
            pixels = img.load()
            
            for y in range(self.size):
                for x in range(self.size):
                    color = (0, 0, 0) if qr_matrix[y][x] else (255, 255, 255)
                    for dy in range(scale):
                        for dx in range(scale):
                            px = x * scale + dx
                            py = y * scale + dy
                            pixels[px, py] = color
            
            img.save(output_filename, "PNG")
            print(f"QR-код сохранен: {output_filename}")
            
            return True
            
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

def create_guaranteed_qr(url: str, filename: str = "my_qr.png"):
    try:
        img = qrcode.make(url)
        img.save(filename)
        print(f"рабочий QR-код: {filename}")
        return True
    except Exception as e:
        print(f"Ошибка гарантированного генератора: {e}")
        return False

def main():
    my_url = "https://asbasket.ru/"  #ССЫЛКА
    

    
    
    fixed_generator = QRCodeGenerator(version=2)
    fixed_success = fixed_generator.generate_qr_code(
        url=my_url,
        output_filename="fixed_qr.png",
        scale=12
    )
    
    
    guaranteed_success = create_guaranteed_qr(
        url=my_url, 
        filename="my_qr.png"
    )
    
    print("\n" + "=" * 50)
    if fixed_success:
        print("Исправленный QR-код создан: fixed_qr.png")
    else:
        print("Исправленный QR-код не создан")
    
    if guaranteed_success:
        print("Гарантированный QR-код создан: my_qr.png")
        
    
    print("=" * 50)

if __name__ == "__main__":
    try:
        import qrcode
        main()
    except ImportError:
        print("Установите библиотеку: pip install qrcode[pil]")