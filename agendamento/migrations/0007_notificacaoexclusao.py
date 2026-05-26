from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0006_cliente_bloqueado'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificacaoExclusao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('servico_nome', models.CharField(max_length=100)),
                ('data_agendamento', models.DateField()),
                ('horario_agendamento', models.TimeField()),
                ('criado_em', models.DateTimeField(default=django.utils.timezone.now)),
                ('visualizado', models.BooleanField(default=False)),
                ('cliente', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notificacoes_exclusao',
                    to='agendamento.cliente',
                )),
            ],
        ),
    ]