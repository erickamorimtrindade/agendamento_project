📅 Sistema de Agendamento Online

📌 Sobre o projeto

Este projeto consiste em um sistema de agendamento online desenvolvido com foco em facilitar a marcação de horários para clientes e a gestão de atendimentos por parte do administrador.

A aplicação permite que usuários visualizem horários disponíveis, realizem agendamentos e que o administrador tenha controle sobre os horários, serviços e disponibilidade.

🚀 Funcionalidades

    👤 Cliente
        Visualizar horários disponíveis
        Realizar agendamentos
        Selecionar serviços
        Interface responsiva para mobile
        Feedback visual ao selecionar horários
        Acesso a pagina "sobre" e "suporte"

    🔧 Administrador
        Criar, editar e excluir horários
        Bloquear horários indisponíveis
        Gerenciar serviços oferecidos
        Visualizar agendamentos realizados
        Visualizar faturamento mensal

    🛠️ Tecnologias utilizadas
        Backend
        Python
        Django
        Frontend
        HTML5
        CSS3
        Bootstrap
        JavaScript
        Bibliotecas e ferramentas
        Flatpickr
        Git e GitHub
📂 Estrutura do projeto
    AGENDAMENTO_PROJECT/
    ├── agendamento/
    │   ├── __pycache__/
    │   ├── migrations/
    │   ├── templates/
    │   │   ├── admin/
    │   │   └── clients/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── forms.py
    │   ├── models.py
    │   ├── tests.py
    │   ├── urls.py
    │   └── views.py
    ├── agendamento_project/
    ├── venv/
    ├── .env
    ├── .gitignore
    ├── db.sqlite3
    ├── manage.py
    ├── README.md
    └── requirements.txt

⚙️ Como rodar o projeto
Pré-requisitos
Python instalado
Git instalado
Passo a passo
# Clonar o repositório
git clone https://github.com/erickamorimtrindade/agendamento_project.git

# Entrar na pasta
cd seu-repo

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Rodar migrações
python manage.py migrate

# Iniciar servidor
python manage.py runserver

Acesse no navegador:

http://127.0.0.1:8000/

📱 Responsividade

O sistema foi desenvolvido com foco em dispositivos móveis, garantindo uma boa experiência para usuários que realizam agendamentos pelo celular.

🔐 Possíveis melhorias futuras

    Notificações por e-mail ou WhatsApp
    Integração com pagamentos online
    Dashboard com relatórios
    Deploy em nuvem
    Bots de mensagens no WhatsApp

🎯 Objetivo

O objetivo deste projeto é, além de consolidar conhecimentos em desenvolvimento backend com Django, oferecer uma solução prática e funcional de agendamento online para pequenos negócios.

A aplicação foi pensada para ser utilizada em cenários reais, com potencial de comercialização, ajudando profissionais a organizarem seus atendimentos e melhorarem a experiência dos seus clientes.

👨‍💻 Autores

Desenvolvido por Erick Amorim e Rafael Maia
[LinkedIn] [https://www.linkedin.com/in/erickamorimtrindade/]
[GitHub] [https://github.com/erickamorimtrindade]

[LinkedIn]
[GitHub]

📄 Licença

Este projeto é de uso privado e possui fins comerciais.

A utilização, cópia, modificação ou distribuição deste software não é permitida sem autorização prévia do autor.