from app import app, db
from models import Cliente, Pedido, Produto

def seed_data():
    with app.app_context():
        # Cria as tabelas caso não existam
        db.create_all()

        # Verifica se já há dados
        if Cliente.query.count() == 0:
            c1 = Cliente(nome="João Silva", telefone="11999998888", email="joao@example.com")
            c2 = Cliente(nome="Maria Fernanda", telefone="11988887777", email="maria@example.com")
            
            p1 = Produto(nome="Agenda Personalizada 2026", preco_venda=150.0)
            p2 = Produto(nome="Caixa Convite Madrinha", preco_venda=80.0)

            db.session.add_all([c1, c2, p1, p2])
            db.session.commit()

            ped1 = Pedido(cliente_id=c1.id, produto_id=p1.id, valor_total=150.0, fase_kanban="Novo Pedido")
            ped2 = Pedido(cliente_id=c2.id, produto_id=p2.id, valor_total=240.0, fase_kanban="Em Produção", descricao="3 caixas")
            ped3 = Pedido(cliente_id=c1.id, produto_id=None, valor_total=90.0, fase_kanban="Primeiro Contato", descricao="Topo de bolo no tema de super heroi")

            db.session.add_all([ped1, ped2, ped3])
            db.session.commit()
            print("Dados semente injetados com sucesso!")
        else:
            print("O banco já possui dados.")

if __name__ == "__main__":
    seed_data()
