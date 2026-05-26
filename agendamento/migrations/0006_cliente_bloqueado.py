from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0005_servico_horario_duplo'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='bloqueado',
            field=models.BooleanField(default=False),
        ),
    ]