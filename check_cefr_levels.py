from app import app
from models import ComputedLevel, Student

def check_cefr_levels():
    with app.app_context():
        # Verificar total de registros
        total_levels = ComputedLevel.query.count()
        print(f"Total de computed levels: {total_levels}")
        
        # Verificar registros com problemas
        problematic_levels = ComputedLevel.query.filter(
            (ComputedLevel.listening_level == None) | 
            (ComputedLevel.listening_level == '') |
            (ComputedLevel.overall_level == None)
        ).all()
        
        print(f"\nRegistros problemáticos: {len(problematic_levels)}")
        
        # Mostrar alguns exemplos
        levels = ComputedLevel.query.join(Student).limit(15).all()
        print("\nPrimeiros 15 registros:")
        for i, level in enumerate(levels):
            print(f"{i+1}. {level.student.name}: "
                  f"Listening_Level={level.listening_level}, "
                  f"Overall='{level.overall_level}', "
                  f"Reading_Level={level.reading_level}")
        
        # Verificar níveis únicos
        unique_listening = ComputedLevel.query.with_entities(ComputedLevel.listening_level).distinct().all()
        unique_overall = ComputedLevel.query.with_entities(ComputedLevel.overall_level).distinct().all()
        print(f"\nNíveis Listening únicos: {[c[0] for c in unique_listening]}")
        print(f"Níveis Overall únicos: {[c[0] for c in unique_overall]}")

if __name__ == "__main__":
    check_cefr_levels()