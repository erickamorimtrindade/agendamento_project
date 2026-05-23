from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0004_merge_20260505_1730'),
    ]

    operations = [
        migrations.AddField(
            model_name='servico',
            name='horario_duplo',
            field=models.BooleanField(
                default=False,
                verbose_name='Ocupa dois horários consecutivos'
            ),
        ),
    ]