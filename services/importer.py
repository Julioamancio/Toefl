import pandas as pd
import os
from datetime import datetime
from models import Student, db
from werkzeug.utils import secure_filename
from listening_csa import compute_listening_csa

class ExcelImporter:
    """Serviço para importação de dados de Excel/CSV"""
    
    # Colunas obrigatórias atualizadas para o novo sistema
    REQUIRED_COLUMNS = [
        'Name', 'StudentNumber', 'Listening', 'TurmaMeta'
    ]
    
    # Colunas opcionais (mantidas para compatibilidade)
    OPTIONAL_COLUMNS = [
        'Reading', 'LFM', 'Total', 'ListCEFR', 'ReadCEFR', 'LFMCEFR', 
        'Lexile', 'OSL', 'MetaNivel'
    ]
    
    # Mapeamento de colunas em português para inglês (atualizado)
    PORTUGUESE_COLUMN_MAPPING = {
        'NOME': 'Name',
        'Nome': 'Name',  # Adicionado para compatibilidade
        'NUMERO': 'StudentNumber',
        'Numero': 'StudentNumber',  # Adicionado para compatibilidade
        'NUMERO_ALUNO': 'StudentNumber',
        'LIST': 'Listening',
        'LISTENING': 'Listening',
        'Listening': 'Listening',  # Adicionado para compatibilidade
        'NLIST': 'ListCEFR',
        'LFM': 'LFM',
        'NLFM': 'LFMCEFR',
        'READ': 'Reading',
        'READING': 'Reading',
        'NREAD': 'ReadCEFR',
        'LEXIL': 'Lexile',
        'LEXILE': 'Lexile',
        'TOTAL': 'Total',
        'META': 'MetaNivel',
        'META_NIVEL': 'MetaNivel',
        'TURMA': 'TurmaMeta',  # Adicionado para mapear coluna Turma
        'Turma': 'TurmaMeta',  # Adicionado para compatibilidade
        'TURMA_META': 'TurmaMeta',
        'META_TURMA': 'TurmaMeta',
        'ROTULO_META': 'TurmaMeta',
        'TURMAMETA': 'TurmaMeta',  # Adicionado para compatibilidade
        'TurmaMeta': 'TurmaMeta'  # Adicionado para compatibilidade
    }
    
    COLUMN_MAPPING = {
        'Name': 'name',
        'StudentNumber': 'student_number',
        'Listening': 'listening',
        'Reading': 'reading',
        'LFM': 'lfm',
        'Total': 'total',
        'ListCEFR': 'list_cefr',
        'ReadCEFR': 'read_cefr',
        'LFMCEFR': 'lfm_cefr',
        'Lexile': 'lexile',
        'OSL': 'cefr_geral',
        'MetaNivel': 'meta_nivel',
        'TurmaMeta': 'turma_meta'  # NOVO CAMPO
    }
    
    def __init__(self, file_path, class_id=None):
        self.file_path = file_path
        self.class_id = class_id
        self.errors = []
        self.warnings = []
        self.processed_count = 0
        self.duplicate_count = 0
        self.error_count = 0
        self.class_info = None
        
        # Carrega informações da turma se class_id foi fornecido
        if self.class_id:
            from models import Class
            self.class_info = Class.query.get(self.class_id)
    
    def get_default_turma_meta(self):
        """Determina o rótulo escolar padrão baseado no nome da turma"""
        if not self.class_info or not self.class_info.name:
            # Se não há informação da turma, usa padrão mais comum
            return '6.2'
            
        class_name = self.class_info.name.lower()
        
        # Verifica se é turma de 6° ano
        if '6' in class_name and ('ano' in class_name or '°' in class_name or 'sexto' in class_name):
            return '6.2'  # Padrão para 6° ano
        
        # Verifica se é turma de 9° ano  
        if '9' in class_name and ('ano' in class_name or '°' in class_name or 'nono' in class_name):
            return '9.2'  # Padrão para 9° ano
            
        # Se não conseguir identificar, usa padrão mais comum (6.2)
        return '6.2'

    def validate_file(self):
        """Valida se o arquivo existe e tem extensão válida"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {self.file_path}")
        
        _, ext = os.path.splitext(self.file_path)
        if ext.lower() not in ['.xlsx', '.xls', '.csv']:
            raise ValueError("Formato de arquivo não suportado. Use .xlsx, .xls ou .csv")
        
        return True
    
    def read_file(self):
        """Lê o arquivo Excel ou CSV"""
        try:
            _, ext = os.path.splitext(self.file_path)
            
            if ext.lower() == '.csv':
                # Tenta diferentes encodings para CSV
                encodings = ['utf-8', 'latin-1', 'cp1252']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(self.file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    raise ValueError("Não foi possível ler o arquivo CSV. Verifique a codificação.")
            else:
                df = pd.read_excel(self.file_path)
            
            # Remove linhas completamente vazias no início
            df = df.dropna(how='all')
            
            # Reset do índice após remover linhas vazias
            df = df.reset_index(drop=True)
            
            return df
        
        except Exception as e:
            raise ValueError(f"Erro ao ler arquivo: {str(e)}")
    
    def validate_columns(self, df):
        """Valida se todas as colunas obrigatórias estão presentes"""
        # Primeiro, mapeia colunas em português para inglês
        for pt_col, en_col in self.PORTUGUESE_COLUMN_MAPPING.items():
            if pt_col in df.columns:
                df.rename(columns={pt_col: en_col}, inplace=True)
        
        # Gera StudentNumber se não existir (baseado no índice + nome)
        if 'StudentNumber' not in df.columns and 'Name' in df.columns:
            def generate_student_number(row):
                name = str(row['Name']) if pd.notna(row['Name']) else 'UNK'
                return f"STU{row.name + 1:04d}_{name[:3].upper()}"
            
            df['StudentNumber'] = df.reset_index().apply(generate_student_number, axis=1)
        
        # Se StudentNumber existe mas está vazio, gera números baseados no índice
        if 'StudentNumber' in df.columns:
            empty_mask = df['StudentNumber'].isna() | (df['StudentNumber'].astype(str).str.strip() == '') | (df['StudentNumber'].astype(str).str.strip() == 'nan')
            if empty_mask.any():
                print(f"DEBUG: Gerando StudentNumber para {empty_mask.sum()} linhas vazias")
                # Usa a coluna Name se existir, senão usa NAME
                name_col = 'Name' if 'Name' in df.columns else 'NAME'
                for idx in df[empty_mask].index:
                    name = str(df.loc[idx, name_col]) if pd.notna(df.loc[idx, name_col]) else 'UNK'
                    df.loc[idx, 'StudentNumber'] = f"STU{idx + 1:04d}_{name[:3].upper()}"
        
        # Adiciona colunas OSL se não existir
        if 'OSL' not in df.columns:
            df['OSL'] = 'N/A'
        
        # Adiciona coluna MetaNivel se não existir (padrão 2 = A2)
        if 'MetaNivel' not in df.columns:
            df['MetaNivel'] = 2
        
        missing_columns = []
        
        # Verifica colunas obrigatórias
        for required_col in self.REQUIRED_COLUMNS:
            if required_col not in df.columns:
                # Tenta encontrar colunas similares (case-insensitive)
                similar_cols = [col for col in df.columns if col.lower() == required_col.lower()]
                if similar_cols:
                    # Renomeia a coluna para o formato padrão
                    df.rename(columns={similar_cols[0]: required_col}, inplace=True)
                else:
                    missing_columns.append(required_col)
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias não encontradas: {', '.join(missing_columns)}")
        
        return df
    
    def clean_data(self, df):
        """Limpa e valida os dados"""
        print(f"DEBUG: Início clean_data - {len(df)} linhas")
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        print(f"DEBUG: Após dropna(how='all') - {len(df)} linhas")
        
        # Remove espaços em branco extras
        string_columns = ['Name', 'ListCEFR', 'ReadCEFR', 'LFMCEFR', 'Lexile', 'OSL']
        for col in string_columns:
            if col in df.columns:
                # Substitui NaN por string vazia antes de converter
                df[col] = df[col].fillna('').astype(str).str.strip()
                # Remove valores 'nan' como string
                df[col] = df[col].replace('nan', '')
        
        # Tratamento especial para StudentNumber - permite IDs alfanuméricos
        if 'StudentNumber' in df.columns:
            # Converte para string primeiro, depois limpa apenas espaços
            df['StudentNumber'] = df['StudentNumber'].fillna('').astype(str).str.strip()
            df['StudentNumber'] = df['StudentNumber'].replace('nan', '')
            # NÃO remove caracteres não numéricos - permite IDs alfanuméricos
        
        # Converte colunas numéricas com tratamento mais cuidadoso
        numeric_columns = ['Listening', 'Reading', 'LFM', 'Total', 'MetaNivel']
        for col in numeric_columns:
            if col in df.columns:
                # Preserva valores originais se já são numéricos
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"DEBUG: Antes da validação de campos obrigatórios - {len(df)} linhas")
        print(f"DEBUG: Primeiras 3 linhas da coluna Name: {df['Name'].head(3).tolist()}")
        print(f"DEBUG: Primeiras 3 linhas da coluna StudentNumber: {df['StudentNumber'].head(3).tolist()}")
        
        # Remove apenas linhas onde Name está completamente vazio ou só espaços
        if 'Name' in df.columns:
            before_name = len(df)
            # Só remove se Name for realmente vazio ou só espaços em branco
            df = df[df['Name'].notna() & (df['Name'].astype(str).str.strip() != '')]
            print(f"DEBUG: Após filtro Name: {before_name} -> {len(df)} linhas")
        
        # StudentNumber será gerado automaticamente se estiver vazio, então não remove linhas
        
        print(f"DEBUG: Final clean_data - {len(df)} linhas")
        return df
    
    def calculate_cefr_level(self, total_score):
        """Calcula o nível CEFR baseado na pontuação total"""
        if pd.isna(total_score):
            return 'N/A'
        
        if total_score >= 800:
            return 'B2'
        elif total_score >= 700:
            return 'B1'
        elif total_score >= 650:
            return 'A2+'
        elif total_score >= 600:
            return 'A2'
        else:
            return 'A1'
    
    def process_row(self, row):
        """Processa uma linha individual do DataFrame"""
        try:
            # Log detalhado da linha sendo processada
            print(f"DEBUG: Processando linha - Name: {row.get('Name', 'N/A')}, StudentNumber: {row.get('StudentNumber', 'N/A')}")
            
            # Verifica se já existe um estudante com o mesmo número
            existing_student = Student.query.filter_by(
                student_number=str(row['StudentNumber'])
            ).first()
            
            if existing_student:
                # Atualiza dados do estudante existente
                print(f"DEBUG: Atualizando estudante existente: {row['Name']} ({row['StudentNumber']})")
                self.update_student(existing_student, row)
                self.duplicate_count += 1
                self.warnings.append(f"Estudante {row['Name']} ({row['StudentNumber']}) atualizado (duplicata)")
            else:
                # Cria novo estudante
                print(f"DEBUG: Criando novo estudante: {row['Name']} ({row['StudentNumber']})")
                self.create_student(row)
                self.processed_count += 1
        
        except Exception as e:
            self.error_count += 1
            error_msg = f"Erro ao processar {row.get('Name', 'N/A')} ({row.get('StudentNumber', 'N/A')}): {str(e)}"
            print(f"DEBUG ERROR: {error_msg}")
            self.errors.append(error_msg)
    
    def create_student(self, row):
        """Cria um novo estudante com o novo sistema TOEFL Junior"""
        try:
            print(f"DEBUG: Iniciando criação do estudante - Name: {row.get('Name')}, StudentNumber: {row.get('StudentNumber')}")
            
            # Função auxiliar para converter valores numéricos
            def safe_int_convert(value):
                if pd.isna(value) or value is None or str(value).strip() == '' or str(value).strip().lower() == 'nan':
                    return None
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return None
            
            # Função auxiliar para converter valores de string
            def safe_str_convert(value):
                if pd.isna(value) or value is None or str(value).strip().lower() == 'nan':
                    return None
                return str(value).strip() if str(value).strip() != '' else None
            
            # Processar list_cefr - calcular automaticamente se for asterisco
            list_cefr_value = safe_str_convert(row.get('ListCEFR'))
            listening_score = safe_int_convert(row.get('Listening'))
            
            # Se list_cefr é asterisco mas temos listening score, calcular automaticamente
            if list_cefr_value == '*' and listening_score is not None:
                from toefl_calculator import cefr_listening
                list_cefr_value = cefr_listening(listening_score)
                print(f"DEBUG: Calculado list_cefr automaticamente: {listening_score} -> {list_cefr_value}")
            
            student = Student(
                name=str(row['Name']),
                student_number=str(row['StudentNumber']),
                listening=listening_score,
                reading=safe_int_convert(row.get('Reading')),
                lfm=safe_int_convert(row.get('LFM')),
                total=safe_int_convert(row.get('Total')),
                list_cefr=list_cefr_value,
                read_cefr=safe_str_convert(row.get('ReadCEFR')),
                lfm_cefr=safe_str_convert(row.get('LFMCEFR')),
                lexile=safe_str_convert(row.get('Lexile')),
                
                class_id=self.class_id
            )
            
            # Calcular CEFR geral automaticamente se total estiver disponível
            if student.total:
                student.cefr_geral = student.calculate_final_cefr()
            
            # Calcular listening_csa_points automaticamente se listening e class_info estiverem disponíveis
            if student.listening and self.class_id:
                try:
                    # Buscar o meta_label da turma
                    from models import Class
                    class_info = Class.query.get(self.class_id)
                    if class_info and class_info.meta_label:
                        rotulo_escolar = float(class_info.meta_label)
                        csa_result = compute_listening_csa(rotulo_escolar, student.listening)
                        student.listening_csa_points = csa_result["points"]
                        print(f"DEBUG: Listening CSA calculado: {student.listening_csa_points}")
                    else:
                        print(f"DEBUG: Não foi possível calcular CSA - meta_label não encontrado")
                except Exception as e:
                    print(f"DEBUG: Erro ao calcular listening CSA: {str(e)}")
            
            print(f"DEBUG: Objeto Student criado com sucesso")
            print(f"DEBUG: Scores - Listening: {student.listening}, Reading: {student.reading}, LFM: {student.lfm}, Total: {student.total}")
            print(f"DEBUG: CEFR Geral calculado: {student.cefr_geral}")
            
            print(f"DEBUG: Adicionando estudante à sessão do banco...")
            db.session.add(student)
            print(f"DEBUG: Estudante {student.name} criado com sucesso")
            return student
            
        except Exception as e:
            print(f"DEBUG ERROR: Erro ao criar estudante {row.get('Name', 'N/A')}: {str(e)}")
            raise e

    def update_student(self, student, row):
        """Atualiza um estudante existente com novos dados"""
        try:
            print(f"DEBUG: Atualizando estudante {student.name}")
            
            # Função auxiliar para converter valores numéricos
            def safe_int_convert(value):
                if pd.isna(value) or value is None or str(value).strip() == '' or str(value).strip().lower() == 'nan':
                    return None
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    return None
            
            # Função auxiliar para converter valores de string
            def safe_str_convert(value):
                if pd.isna(value) or value is None or str(value).strip().lower() == 'nan':
                    return None
                return str(value).strip() if str(value).strip() != '' else None
            
            # Processar list_cefr - calcular automaticamente se for asterisco
            list_cefr_value = safe_str_convert(row.get('ListCEFR'))
            listening_score = safe_int_convert(row.get('Listening'))
            
            # Se list_cefr é asterisco mas temos listening score, calcular automaticamente
            if list_cefr_value == '*' and listening_score is not None:
                from toefl_calculator import cefr_listening
                list_cefr_value = cefr_listening(listening_score)
                print(f"DEBUG: Calculado list_cefr automaticamente: {listening_score} -> {list_cefr_value}")
            
            # Atualiza campos básicos usando as mesmas funções auxiliares
            student.name = str(row['Name'])
            student.listening = listening_score
            student.reading = safe_int_convert(row.get('Reading'))
            student.lfm = safe_int_convert(row.get('LFM'))
            student.total = safe_int_convert(row.get('Total'))
            student.list_cefr = list_cefr_value
            student.read_cefr = safe_str_convert(row.get('ReadCEFR'))
            student.lfm_cefr = safe_str_convert(row.get('LFMCEFR'))
            student.lexile = safe_str_convert(row.get('Lexile'))
            
            # Calcular CEFR geral automaticamente se total estiver disponível
            if student.total:
                student.cefr_geral = student.calculate_final_cefr()
            
            # Calcular listening_csa_points automaticamente se listening e class_info estiverem disponíveis
            if student.listening and self.class_id:
                try:
                    # Buscar o meta_label da turma
                    from models import Class
                    class_info = Class.query.get(self.class_id)
                    if class_info and class_info.meta_label:
                        rotulo_escolar = float(class_info.meta_label)
                        csa_result = compute_listening_csa(rotulo_escolar, student.listening)
                        student.listening_csa_points = csa_result["points"]
                        print(f"DEBUG: Listening CSA atualizado: {student.listening_csa_points}")
                    else:
                        print(f"DEBUG: Não foi possível calcular CSA - meta_label não encontrado")
                except Exception as e:
                    print(f"DEBUG: Erro ao calcular listening CSA: {str(e)}")

            # Atualiza turma se especificada
            if self.class_id:
                student.class_id = self.class_id
            
            print(f"DEBUG: Estudante {student.name} atualizado com sucesso")
            
        except Exception as e:
            print(f"DEBUG ERROR: Erro ao atualizar estudante {student.name}: {str(e)}")
            raise e

    def validate_turma_meta(self, turma_meta):
        """Valida se o rótulo da turma meta é válido"""
        valid_labels = ["6.1", "6.2", "6.3", "9.1", "9.2", "9.3"]
        return turma_meta in valid_labels

    def validate_row_data(self, row, row_index):
        """Valida os dados de uma linha específica"""
        errors = []
        
        # Validar nome
        if pd.isna(row.get('Name')) or str(row.get('Name')).strip() == '':
            errors.append(f"Linha {row_index + 2}: Nome é obrigatório")
        
        # Validar número do estudante
        if pd.isna(row.get('StudentNumber')) or str(row.get('StudentNumber')).strip() == '':
            errors.append(f"Linha {row_index + 2}: Número do estudante é obrigatório")
        
        # Validar pontuação de Listening
        if pd.isna(row.get('Listening')):
            errors.append(f"Linha {row_index + 2}: Pontuação de Listening é obrigatória")
        else:
            try:
                listening_score = int(row.get('Listening'))
                if listening_score < 200 or listening_score > 300:
                    errors.append(f"Linha {row_index + 2}: Pontuação de Listening deve estar entre 200-300")
            except (ValueError, TypeError):
                errors.append(f"Linha {row_index + 2}: Pontuação de Listening deve ser um número")
        
        # Validar meta da turma
        if pd.notna(row.get('TurmaMeta')):
            turma_meta = str(row.get('TurmaMeta')).strip()
            if not self.validate_turma_meta(turma_meta):
                errors.append(f"Linha {row_index + 2}: Meta da turma deve ser um dos valores: 6.1, 6.2, 6.3, 9.1, 9.2, 9.3")
        
        return errors

    def import_data(self):
        """Executa o processo completo de importação"""
        try:
            # Valida e lê arquivo
            self.validate_file()
            df = self.read_file()
            
            # Valida colunas e limpa dados
            df = self.validate_columns(df)
            df = self.clean_data(df)
            
            # Processa cada linha
            for index, row in df.iterrows():
                self.process_row(row)
                
                # Commit a cada 50 registros para evitar problemas de memória
                if (index + 1) % 50 == 0:
                    db.session.commit()
            
            # Commit final
            db.session.commit()
            
            return {
                'success': True,
                'processed': self.processed_count,
                'duplicates': self.duplicate_count,
                'errors': self.error_count,
                'error_messages': self.errors,
                'warnings': self.warnings
            }
        
        except Exception as e:
            # Em caso de erro, reverte transação
            db.session.rollback()
            
            return {
                'success': False,
                'error': str(e),
                'processed': self.processed_count,
                'duplicates': self.duplicate_count,
                'errors': self.error_count + 1
            }
    
    def preview_data(self, max_rows=10):
        """Gera uma prévia dos dados sem importar"""
        try:
            from toefl_calculator import cefr_listening, school_label, grade_listening
            import numpy as np
            
            self.validate_file()
            df = self.read_file()
            print(f"DEBUG: Após read_file - {len(df)} linhas")
            print(f"DEBUG: Colunas após read_file: {list(df.columns)}")
            
            df = self.validate_columns(df)
            print(f"DEBUG: Após validate_columns - {len(df)} linhas")
            print(f"DEBUG: Colunas após validate_columns: {list(df.columns)}")
            
            df = self.clean_data(df)
            print(f"DEBUG: Após clean_data - {len(df)} linhas")
            
            # Adiciona colunas do novo sistema TOEFL Junior
            if 'Listening' in df.columns:
                df['CEFR_Listening'] = df['Listening'].apply(lambda x: cefr_listening(x) if pd.notna(x) else '')
                df['School_Label'] = df['Listening'].apply(lambda x: school_label(x) if pd.notna(x) else '')
                
                # Adiciona nota calculada se meta estiver disponível
                if 'TurmaMeta' in df.columns:
                    df['Nota_Listening'] = df.apply(
                        lambda row: grade_listening(row['Listening'], row['TurmaMeta']) 
                        if pd.notna(row['Listening']) and pd.notna(row['TurmaMeta']) else '',
                        axis=1
                    )
            
            # Adiciona coluna de nível CEFR calculado (legado)
            if 'Total' in df.columns:
                df['Calculated_CEFR'] = df['Total'].apply(self.calculate_cefr_level)
            
            # Retorna apenas as primeiras linhas
            preview_df = df.head(max_rows)
            
            # Substitui valores NaN, inf e -inf por None para serialização JSON correta
            preview_df = preview_df.replace([np.nan, np.inf, -np.inf], None)
            
            # Converte para dict e garante que não há valores problemáticos
            preview_data = preview_df.to_dict('records')
            
            # Limpa qualquer valor NaN restante
            for record in preview_data:
                for key, value in record.items():
                    if pd.isna(value) or value is np.nan:
                        record[key] = None
            
            return {
                'success': True,
                'total_rows': len(df),
                'preview_data': preview_data,
                'columns': list(df.columns)
            }
        
        except Exception as e:
            print(f"DEBUG: Erro na preview_data: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }