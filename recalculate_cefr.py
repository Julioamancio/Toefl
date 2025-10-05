import sys
from app import create_app
from models import db, Student, ComputedLevel, calculate_student_levels

def main():
    app, csrf = create_app()
    with app.app_context():
        students = Student.query.all()
        updated = 0
        created = 0
        updated_cefr_geral = 0
        errors = []

        for student in students:
            try:
                levels, applied_rules = calculate_student_levels(student)

                # Update or create ComputedLevel
                computed = ComputedLevel.query.filter_by(student_id=student.id).first()
                if computed:
                    computed.school_level = levels.get('school_level')
                    computed.listening_level = levels.get('listening_level')
                    computed.lfm_level = levels.get('lfm_level')
                    computed.reading_level = levels.get('reading_level')
                    computed.overall_level = levels.get('overall_level')
                    computed.applied_rules = "\n".join(applied_rules)
                    updated += 1
                else:
                    computed = ComputedLevel(
                        student_id=student.id,
                        school_level=levels.get('school_level'),
                        listening_level=levels.get('listening_level'),
                        lfm_level=levels.get('lfm_level'),
                        reading_level=levels.get('reading_level'),
                        overall_level=levels.get('overall_level'),
                        applied_rules="\n".join(applied_rules),
                    )
                    db.session.add(computed)
                    created += 1

                # Also update Student.cefr_geral to match new overall level
                new_overall = levels.get('overall_level')
                if new_overall and student.cefr_geral != new_overall:
                    student.cefr_geral = new_overall
                    updated_cefr_geral += 1

            except Exception as e:
                errors.append(f"Erro no estudante {student.id} ({student.name}): {e}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Falha ao salvar alterações: {e}")
            sys.exit(1)

        print(
            f"Recalculo concluído. ComputedLevel atualizados: {updated}, criados: {created}, "
            f"cefr_geral atualizados: {updated_cefr_geral}."
        )
        if errors:
            print(f"Ocorreram {len(errors)} erros:")
            for err in errors[:10]:
                print(" -", err)

if __name__ == "__main__":
    main()