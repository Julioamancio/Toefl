"""
Serviço para geração de certificados TOEFL Junior com imagem personalizada
"""

from PIL import Image, ImageDraw, ImageFont
import os
import io
import json
import logging
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 566
IMAGE_WIDTH = 2000
IMAGE_HEIGHT = 1414
CANVAS_TO_IMAGE_SCALE = IMAGE_WIDTH / CANVAS_WIDTH

logger = logging.getLogger('certificate')

class CertificateGenerator:
    """Gerador de certificados TOEFL Junior"""
    
    def __init__(self):
        self.template_path = str(BASE_DIR / 'static' / 'templates' / 'certificate_template.png')
        self.default_layout_path = str(BASE_DIR / 'static' / 'default_certificate_layout.json')
        self._load_default_layout()
    
    def _load_default_layout(self):
        """Carrega o layout padrão do arquivo JSON"""
        try:
            if os.path.exists(self.default_layout_path):
                with open(self.default_layout_path, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                    raw_positions = layout_data.get('positions', {}) or {}
                    self.raw_default_positions = raw_positions
                    self.default_positions = self._convert_layout_positions_to_pixels(raw_positions)
                    self.default_colors = layout_data.get('colors', {}) or {}
                    logger.info('layout loaded', extra={'positions': self.default_positions})
            else:
                logger.warning('layout file missing', extra={'path': str(self.default_layout_path)})
                self._set_fallback_layout()
        except Exception as e:
            logger.exception('failed to load layout: %s', e)
            self._set_fallback_layout()

    def _set_fallback_layout(self):
        """Define layout de fallback caso o arquivo não seja encontrado"""
        fallback_positions = {
            'studentName': {'x': 401, 'y': 237, 'font_size': 78},
            'listeningScore': {'x': 418, 'y': 337, 'font_size': 40},
            'readingScore': {'x': 626, 'y': 336, 'font_size': 40},
            'lfmScore': {'x': 419, 'y': 365, 'font_size': 40},
            'totalScore': {'x': 626, 'y': 366, 'font_size': 40},
            'testDate': {'x': 297, 'y': 414, 'font_size': 40}
        }
        self.raw_default_positions = fallback_positions
        self.default_positions = self._convert_layout_positions_to_pixels(fallback_positions)
        self.default_colors = {
            'name_color': '#000000',
            'scores_color': '#000000',
            'date_color': '#000000'
        }

    def _convert_layout_positions_to_pixels(self, positions):
        """Converte posições salvas (percentuais ou pixels) para coordenadas em pixels da imagem final."""
        normalized = {}
        for key, raw_pos in (positions or {}).items():
            if not isinstance(raw_pos, dict):
                continue
            try:
                x_value = float(raw_pos.get('x'))
                y_value = float(raw_pos.get('y'))
            except (TypeError, ValueError):
                continue
            font_size_value = raw_pos.get('font_size')
            is_percentage = False
            x = x_value
            y = y_value
            if -1 <= x_value <= 1 and -1 <= y_value <= 1:
                x = x_value * IMAGE_WIDTH
                y = y_value * IMAGE_HEIGHT
                is_percentage = True
            elif 0 <= x_value <= 100 and 0 <= y_value <= 100:
                x = (x_value / 100.0) * IMAGE_WIDTH
                y = (y_value / 100.0) * IMAGE_HEIGHT
                is_percentage = True
            entry = {'x': int(round(x)), 'y': int(round(y))}
            if font_size_value is not None:
                try:
                    font_size_float = float(font_size_value)
                except (TypeError, ValueError):
                    font_size_float = None
                if font_size_float is not None:
                    if is_percentage:
                        entry['font_size'] = int(round(font_size_float * CANVAS_TO_IMAGE_SCALE))
                    else:
                        entry['font_size'] = int(round(font_size_float))
            normalized[key] = entry
        return normalized

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
        logger.debug('applying custom positions', extra={'positions': custom_positions})
        """
        Atualiza as coordenadas padrão com posições personalizadas
        
        Args:
            custom_positions (dict): Posições personalizadas no formato:
                {
                    'studentName': {'x': 100, 'y': 200, 'font_size': 16},
                    'listeningScore': {'x': 150, 'y': 250, 'font_size': 14},
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
        
        # Dimensões do canvas (tamanho real de exibição)
        global CANVAS_WIDTH, CANVAS_HEIGHT

        # Dimensões da imagem original para geração do certificado
        global IMAGE_WIDTH, IMAGE_HEIGHT
        
        # Atualizar coordenadas padrão
        for frontend_id, position in custom_positions.items():
            if frontend_id in field_mapping:
                logger.debug('field update', extra={'field': frontend_id, 'position': position})
                field_name = field_mapping[frontend_id]
                
                # Converter percentuais para pixels usando as dimensões da imagem final
                x_pixels = (position['x'] / 100) * IMAGE_WIDTH
                y_pixels = (position['y'] / 100) * IMAGE_HEIGHT
                
                self._custom_coordinates[field_name] = {
                    'x': int(x_pixels),
                    'y': int(y_pixels)
                }
                # Incluir font_size se fornecido e escalar proporcionalmente
                if 'font_size' in position:
                    # Escalar font_size do canvas (800x566) para imagem final (2000x1414)
                    scaled_font_size = int(position['font_size'] * CANVAS_TO_IMAGE_SCALE)
                    self._custom_coordinates[field_name]['font_size'] = scaled_font_size
                    
    def _get_coordinates(self, custom_colors=None):
        """
        Retorna coordenadas e configurações para todos os campos do certificado
        
        Args:
            custom_colors (dict): Cores personalizadas para os campos (opcional)
        
        Returns:
            dict: Coordenadas e configurações para cada campo
        """
        # Cores padrão
        default_colors = {
            'student_name': (0, 0, 0),  # Preto
            'scores': (0, 0, 0),        # Preto
            'date': (0, 0, 0)           # Preto
        }
        
        layout_default_colors = getattr(self, 'default_colors', {}) or {}
        layout_color_map = {
            'student_name': layout_default_colors.get('name_color'),
            'scores': layout_default_colors.get('scores_color'),
            'date': layout_default_colors.get('date_color')
        }
        for field, color_value in layout_color_map.items():
            parsed_color = self._parse_color_input(color_value) if color_value else None
            if parsed_color:
                default_colors[field] = parsed_color

        # Processar cores personalizadas
        colors = {}
        required_fields = ['student_name', 'scores', 'date']
        
        for field in required_fields:
            if custom_colors and field in custom_colors:
                parsed_color = self._parse_color_input(custom_colors[field])
                colors[field] = parsed_color if parsed_color else default_colors[field]
            else:
                colors[field] = default_colors[field]
        
        # Usar coordenadas do layout padrão carregado do JSON
        field_mapping = {
            'studentName': 'student_name',
            'listeningScore': 'listening_score', 
            'readingScore': 'reading_score',
            'lfmScore': 'lfm_score',
            'totalScore': 'overall_score',
            'testDate': 'test_date'
        }
        
        coordinates = {}
        
        # Mapear posições do layout padrão para coordenadas do certificado
        for frontend_id, backend_field in field_mapping.items():
            if frontend_id in self.default_positions:
                pos = self.default_positions[frontend_id]
                
                # Determinar cor baseada no campo
                if backend_field == 'student_name':
                    field_color = colors['student_name']
                elif backend_field == 'test_date':
                    field_color = colors['date']
                else:
                    field_color = colors['scores']
                
                coordinates[backend_field] = {
                    'x': pos['x'],
                    'y': pos['y'],
                    'font_size': pos.get('font_size', 16),
                    'color': field_color,
                    'font_weight': 'bold' if backend_field == 'student_name' else 'normal'
                }
        
        # Aplicar coordenadas personalizadas se existirem
        if hasattr(self, '_custom_coordinates') and self._custom_coordinates:
            for field_name, custom_pos in self._custom_coordinates.items():
                if field_name in coordinates:
                    coordinates[field_name]['x'] = custom_pos['x']
                    coordinates[field_name]['y'] = custom_pos['y']
                    # Aplicar font_size personalizado se fornecido
                    if 'font_size' in custom_pos:
                        coordinates[field_name]['font_size'] = custom_pos['font_size']
        
        return coordinates
    
    def _get_font(self, size, weight='normal'):
        """Obtém fonte apropriada para o texto"""
        font_candidates = []

        static_font_dir = BASE_DIR / 'static' / 'fonts'
        # Priorizar fontes locais incluídas no projeto para evitar fallback minúsculo
        if weight == 'bold':
            font_candidates.extend([
                static_font_dir / 'DejaVuSans-Bold.ttf'
            ])
            font_candidates.extend([
                static_font_dir / 'OpenSans-Bold.ttf',
                static_font_dir / 'Montserrat-Bold.ttf',
                static_font_dir / 'NotoSans-Bold.ttf',
                static_font_dir / 'NotoSansDisplay-Bold.ttf',
                Path('arialbd.ttf'),
                Path('Arial Bold.ttf')
            ])
        else:
            font_candidates.extend([
                static_font_dir / 'DejaVuSans.ttf'
            ])
            font_candidates.extend([
                static_font_dir / 'OpenSans-Regular.ttf',
                static_font_dir / 'Montserrat-Regular.ttf',
                static_font_dir / 'NotoSans-Regular.ttf',
                static_font_dir / 'NotoSansDisplay-Regular.ttf',
                Path('arial.ttf'),
                Path('Arial.ttf')
            ])

        try:
            from PIL import ImageFont as PILImageFontModule
            pil_font_dir = Path(PILImageFontModule.__file__).resolve().parent / 'fonts'
            if weight == 'bold':
                font_candidates.append(pil_font_dir / 'DejaVuSans-Bold.ttf')
            else:
                font_candidates.append(pil_font_dir / 'DejaVuSans.ttf')
        except Exception:
            pass

        for candidate in font_candidates:
            try:
                candidate_path = Path(candidate)
                if candidate_path.is_file():
                    return ImageFont.truetype(str(candidate_path), size)
                elif candidate_path.exists():
                    return ImageFont.truetype(str(candidate_path), size)
            except Exception:
                continue

        try:
            return ImageFont.truetype('DejaVuSans.ttf', size)
        except Exception:
            pass

        try:
            return ImageFont.truetype('LiberationSans-Regular.ttf', size)
        except Exception:
            pass

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
            logger.exception('error saving certificate: %s', e)
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

def create_certificate_for_student(student, custom_colors=None, custom_positions=None, custom_date=None):
    """
    Função auxiliar para criar certificado a partir de um objeto Student
    
    Args:
        student: Objeto Student do SQLAlchemy
        custom_colors (dict): Cores personalizadas para os campos (opcional)
        custom_positions (dict): Posições personalizadas para os elementos (opcional)
        custom_date (str): Data personalizada para o certificado (opcional)
    
    Returns:
        io.BytesIO: Buffer com os dados da imagem do certificado
    """
    generator = CertificateGenerator()
    
    # Garantir que o layout padrão esteja carregado
    if not hasattr(generator, 'default_positions') or not generator.default_positions:
        generator._load_default_layout()
    
    # Se posições personalizadas foram fornecidas, atualizar as coordenadas
    if custom_positions:
        logger.info('custom positions received', extra={'positions': custom_positions})
        generator._update_coordinates(custom_positions)
    else:
        logger.info('using default positions only')
    
    # Usar data personalizada se fornecida, senão usar data atual
    test_date = custom_date if custom_date else datetime.now().strftime("%d/%m/%Y")
    
    # Usar o nome encontrado (found_name) quando disponível; caso contrário, cair para name
    # Determinar nome a exibir: usar found_name quando existir, senão cair para name
    try:
        display_name_raw = (student.found_name or student.name or '').strip()
    except Exception:
        display_name_raw = (getattr(student, 'name', '') or '').strip()

    # Reduzir para Primeiro + Último nome
    if display_name_raw:
        parts = [p for p in re.split(r"\s+", display_name_raw) if p]
        if len(parts) >= 2:
            display_name = f"{parts[0]} {parts[-1]}"
        else:
            display_name = parts[0]
    else:
        display_name = ''

    student_data = {
        'name': display_name,
        'listening': student.listening,
        'reading': student.reading,
        'lfm': student.lfm,
        'total': student.total,
        'test_date': test_date
    }
    
    return generator.generate_certificate_bytes(student_data, custom_colors)