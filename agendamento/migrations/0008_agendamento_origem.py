from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0007_notificacaoexclusao'),
    ]

    operations = [
        migrations.AddField(
            model_name='agendamento',
            name='origem',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('online', 'Online'),
                    ('manual', 'Manual'),
                ],
                default='online',
                verbose_name='Origem',
            ),
        ),
        # Campos extras para agendamentos manuais (sem vínculo com Cliente cadastrado)
        migrations.AddField(
            model_name='agendamento',
            name='nome_manual',
            field=models.CharField(
                max_length=100,
                blank=True,
                default='',
                verbose_name='Nome (agendamento manual)',
            ),
        ),
        migrations.AddField(
            model_name='agendamento',
            name='telefone_manual',
            field=models.CharField(
                max_length=20,
                blank=True,
                default='',
                verbose_name='Telefone (agendamento manual)',
            ),
        ),
        # Torna cliente opcional para suportar agendamentos manuais
        migrations.AlterField(
            model_name='agendamento',
            name='cliente',
            field=models.ForeignKey(
                'agendamento.Cliente',
                on_delete=models.CASCADE,
                null=True,
                blank=True,
            ),
        ),
    ]