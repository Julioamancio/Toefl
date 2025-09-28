"""
Serviço para geração de certificados TOEFL Junior com imagem personalizada
"""

from PIL import Image, ImageDraw, ImageFont
import os
import io
from datetime import datetime

class CertificateGenerator:
    """Gerador de certificados TOEFL Junior"""
    
    def __init__(self):
        self.template_path = os.path.join('static', 'templates', 'certificate_template.png')
        # Removido: cores padrão hardcoded - devem vir do editor
    
    def _validate_color(self, color):
        """Valida se a cor está no formato RGB correto"""
        if isinstance(color, (tuple, list)) and len(color) == 3:
            return all(isinstance(c, int) and 0 <= c <= 255 for c in color)
        return False
    
    def _convert_color_name_to_rgb(self, color_name):
        """Converte nome da cor para RGB"""
        color_map = {
            # Cores básicas
            'preto': (0, 0, 0),
            'branco': (255, 255, 255),
            'vermelho': (255, 0, 0),
            'verde': (0, 255, 0),
            'azul': (0, 0, 255),
            'amarelo': (255, 255, 0),
            'magenta': (255, 0, 255),
            'ciano': (0, 255, 255),
            
            # Tons de azul
            'azul_escuro': (0, 0, 139),
            'azul_medio': (0, 0, 205),
            'azul_claro': (173, 216, 230),
            'azul_marinho': (0, 0, 128),
            'azul_real': (65, 105, 225),
            
            # Tons de vermelho
            'vermelho_escuro': (139, 0, 0),
            'vermelho_claro': (255, 182, 193),
            'rosa': (255, 192, 203),
            'rosa_escuro': (199, 21, 133),
            
            # Tons de verde
            'verde_escuro': (0, 100, 0),
            'verde_claro': (144, 238, 144),
            'verde_lima': (50, 205, 50),
            'verde_floresta': (34, 139, 34),
            
            # Tons de cinza
            'cinza': (128, 128, 128),
            'cinza_escuro': (64, 64, 64),
            'cinza_claro': (192, 192, 192),
            
            # Outras cores
            'laranja': (255, 165, 0),
            'roxo': (128, 0, 128),
            'marrom': (165, 42, 42),
            'dourado': (255, 215, 0),
            'prata': (192, 192, 192),
            
            # Cores padrão do sistema
            'padrao_nome': (0, 0, 100),
            'padrao_pontuacao': (0, 0, 128),
            'padrao_data': (0, 0, 128)
        }
        
        return color_map.get(color_name.lower(), None)
    
    def _convert_hex_to_rgb(self, hex_color):
        """Converte cor hexadecimal para RGB"""
        try:
            # Remove o # se presente
            hex_color = hex_color.lstrip('#')
            
            # Verifica se tem 6 caracteres
            if len(hex_color) != 6:
                return None
                
            # Converte para RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            return (r, g, b)
        except:
            return None
    
    def _parse_color_input(self, color_input):
        """
        Converte entrada de cor em RGB
        Aceita: tupla RGB, nome da cor, ou hex
        """
        if color_input is None:
            return None
            
        # Se já é uma tupla RGB válida
        if self._validate_color(color_input):
            return tuple(color_input)
        
        # Se é string (nome ou hex)
        if isinstance(color_input, str):
            # Tenta converter nome da cor
            rgb_from_name = self._convert_color_name_to_rgb(color_input)
            if rgb_from_name:
                return rgb_from_name
            
            # Tenta converter hex
            rgb_from_hex = self._convert_hex_to_rgb(color_input)
            if rgb_from_hex:
                return rgb_from_hex
        
        return None
    
    def _update_coordinates(self, custom_positions):
        """
        Atualiza as coordenadas padrão com posições personalizadas
        
        Args:
            custom_positions (dict): Posições personalizadas no formato:
                {
                    'studentName': {'x': 100, 'y': 200},
                    'listeningScore': {'x': 150, 'y': 250},
                    ...
                }
        """
        # Mapeamento entre IDs do frontend e campos do certificado
        field_mapping = {
            'studentName': 'student_name',
            'listeningScore': 'listening_score',
            'readingScore': 'reading_score',
            'lfmScore': 'lfm_score',
            'totalScore': 'overall_score',
            'testDate': 'test_date'
        }
        
        # Inicializar coordenadas personalizadas se não existir
        if not hasattr(self, '_custom_coordinates'):
            self._custom_coordinates = {}
        
        # Atualizar coordenadas padrão
        for frontend_id, position in custom_positions.items():
            if frontend_id in field_mapping:
                field_name = field_mapping[frontend_id]
                self._custom_coordinates[field_name] = {
                    'x': position['x'],
                    'y': position['y']
                }
                    
    def _get_coordinates(self, custom_colors=None):
        """
        Define as coordenadas dos campos no certificado
        
        Args:
            custom_colors (dict): Cores personalizadas para os campos (opcional)
                Formato: {
                    'student_name': (r, g, b) ou 'nome_cor' ou '#hex',
                    'scores': (r, g, b) ou 'nome_cor' ou '#hex',
                    'date': (r, g, b) ou 'nome_cor' ou '#hex'
                }
        """
        # Cores padrão caso não sejam fornecidas
        default_colors = {
            'student_name': (0, 0, 0),  # Preto
            'scores': (0, 0, 0),        # Preto
            'date': (0, 0, 0)           # Preto
        }
        
        # Processar cores fornecidas ou usar padrão
        colors = {}
        required_fields = ['student_name', 'scores', 'date']
        
        for field in required_fields:
            if custom_colors and field in custom_colors:
                parsed_color = self._parse_color_input(custom_colors[field])
                colors[field] = parsed_color if parsed_color else default_colors[field]
            else:
                colors[field] = default_colors[field]
        
        # Coordenadas base (padrão ou personalizadas)
        default_coordinates = {
            'student_name': {'x': 350, 'y': 355},
            'listening_score': {'x': 370, 'y': 403},
            'reading_score': {'x': 485, 'y': 403},
            'lfm_score': {'x': 370, 'y': 418},
            'overall_score': {'x': 485, 'y': 418},
            'test_date': {'x': 420, 'y': 442}
        }
        
        coordinates = {
            'student_name': {
                'x': default_coordinates['student_name']['x'],
                'y': default_coordinates['student_name']['y'],
                'font_size': 100,
                'color': colors['student_name'],
                'font_weight': 'bold'
            },
            'listening_score': {
                'x': default_coordinates['listening_score']['x'],
                'y': default_coordinates['listening_score']['y'],
                'font_size': 14,
                'color': colors['scores'],
                'font_weight': 'normal'
            },
            'reading_score': {
                'x': default_coordinates['reading_score']['x'],
                'y': default_coordinates['reading_score']['y'],
                'font_size': 14,
                'color': colors['scores'],
                'font_weight': 'normal'
            },
            'lfm_score': {
                'x': default_coordinates['lfm_score']['x'],
                'y': default_coordinates['lfm_score']['y'],
                'font_size': 14,
                'color': colors['scores'],
                'font_weight': 'normal'
            },
            'overall_score': {
                'x': default_coordinates['overall_score']['x'],
                'y': default_coordinates['overall_score']['y'],
                'font_size': 14,
                'color': colors['scores'],
                'font_weight': 'normal'
            },
            'test_date': {
                'x': default_coordinates['test_date']['x'],
                'y': default_coordinates['test_date']['y'],
                'font_size': 12,
                'color': colors['date'],
                'font_weight': 'normal'
            }
        }
        
        # Aplicar coordenadas personalizadas se existirem
        if hasattr(self, '_custom_coordinates') and self._custom_coordinates:
            for field_name, custom_pos in self._custom_coordinates.items():
                if field_name in coordinates:
                    coordinates[field_name]['x'] = custom_pos['x']
                    coordinates[field_name]['y'] = custom_pos['y']
        
        return coordinates
    
    def _get_font(self, size, weight='normal'):
        """Obtém fonte apropriada para o texto"""
        try:
            if weight == 'bold':
                return ImageFont.truetype("arialbd.ttf", size)
            else:
                return ImageFont.truetype("arial.ttf", size)
        except:
            # Fallback para fonte padrão
            return ImageFont.load_default()
    
    def generate_certificate(self, student_data, custom_colors=None):
        """
        Gera certificado personalizado para um estudante
        
        Args:
            student_data (dict): Dados do estudante contendo:
                - name: Nome do estudante
                - listening: Pontuação em Listening
                - reading: Pontuação em Reading
                - lfm: Pontuação em Language Form & Meaning
                - total: Pontuação total/overall
                - test_date: Data do teste (opcional)
            custom_colors (dict): Cores personalizadas para os campos (opcional)
                Formato: {
                    'student_name': (r, g, b),
                    'scores': (r, g, b),
                    'date': (r, g, b)
                }
        
        Returns:
            PIL.Image: Imagem do certificado gerado
        """
        
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Template não encontrado: {self.template_path}")
        
        # Obter coordenadas com cores personalizadas
        coordinates = self._get_coordinates(custom_colors)
        
        # Abrir template
        template = Image.open(self.template_path)
        certificate = template.copy()
        draw = ImageDraw.Draw(certificate)
        
        # Data do teste (usar atual se não fornecida)
        test_date = student_data.get('test_date', datetime.now().strftime("%d/%m/%Y"))
        
        # Mapear dados para os campos
        fields_data = {
            'student_name': student_data.get('name', 'N/A'),
            'listening_score': str(student_data.get('listening', 'N/A')),
            'reading_score': str(student_data.get('reading', 'N/A')),
            'lfm_score': str(student_data.get('lfm', 'N/A')),
            'overall_score': str(student_data.get('total', 'N/A')),
            'test_date': test_date
        }
        
        # Adicionar texto aos campos
        for field_name, text in fields_data.items():
            if field_name in coordinates:
                coords = coordinates[field_name]
                font = self._get_font(coords['font_size'], coords.get('font_weight', 'normal'))
                
                draw.text(
                    (coords['x'], coords['y']),
                    text,
                    fill=coords['color'],
                    font=font
                )
        
        return certificate
    
    def generate_certificate_bytes(self, student_data, custom_colors=None, format='PNG'):
        """
        Gera certificado e retorna como bytes para download
        
        Args:
            student_data (dict): Dados do estudante
            custom_colors (dict): Cores personalizadas para os campos (opcional)
            format (str): Formato da imagem ('PNG', 'JPEG', etc.)
        
        Returns:
            io.BytesIO: Buffer com os dados da imagem
        """
        certificate = self.generate_certificate(student_data, custom_colors)
        
        # Converter para bytes
        img_buffer = io.BytesIO()
        certificate.save(img_buffer, format=format, quality=95)
        img_buffer.seek(0)
        
        return img_buffer
    
    def save_certificate(self, student_data, output_path, custom_colors=None, format='PNG'):
        """
        Gera e salva certificado em arquivo
        
        Args:
            student_data (dict): Dados do estudante
            output_path (str): Caminho para salvar o arquivo
            custom_colors (dict): Cores personalizadas para os campos (opcional)
            format (str): Formato da imagem
        
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            certificate = self.generate_certificate(student_data, custom_colors)
            
            # Criar diretório se não existir
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            certificate.save(output_path, format=format, quality=95)
            return True
        except Exception as e:
            print(f"Erro ao salvar certificado: {e}")
            return False

    def set_default_colors(self, student_name_color=None, scores_color=None, date_color=None):
        """
        FUNÇÃO REMOVIDA: Não há mais cores padrão - todas devem vir do editor
        """
        raise NotImplementedError("Cores padrão foram removidas. Configure as cores no editor.")
    
    def get_current_colors(self):
        """
        FUNÇÃO REMOVIDA: Não há mais cores padrão - todas devem vir do editor
        """
        raise NotImplementedError("Cores padrão foram removidas. Configure as cores no editor.")
    
    def reset_colors_to_default(self):
        """
        FUNÇÃO REMOVIDA: Não há mais cores padrão - todas devem vir do editor
        """
        raise NotImplementedError("Cores padrão foram removidas. Configure as cores no editor.")

def create_certificate_for_student(student, custom_colors=None, custom_positions=None):
    """
    Função auxiliar para criar certificado a partir de um objeto Student
    
    Args:
        student: Objeto Student do SQLAlchemy
        custom_colors (dict): Cores personalizadas para os campos (opcional)
        custom_positions (dict): Posições personalizadas para os elementos (opcional)
    
    Returns:
        io.BytesIO: Buffer com os dados da imagem do certificado
    """
    generator = CertificateGenerator()
    
    # Se posições personalizadas foram fornecidas, atualizar as coordenadas
    if custom_positions:
        generator._update_coordinates(custom_positions)
    
    student_data = {
        'name': student.name,
        'listening': student.listening,
        'reading': student.reading,
        'lfm': student.lfm,
        'total': student.total,
        'test_date': datetime.now().strftime("%d/%m/%Y")
    }
    
    return generator.generate_certificate_bytes(student_data, custom_colors)