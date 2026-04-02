from app import app, db
from models import Cliente, Pedido, Produto, ConfiguracaoOperacional, CustoFixo, Equipamento, Material, Desgaste

def seed_advanced():
    with app.app_context():
        db.drop_all() # Reseta o banco antigo que conflita com os modelos
        db.create_all()

        # 1. Configurações da Fabriqueta
        config = ConfiguracaoOperacional(
            dias_trabalhados=22,
            horas_por_dia=8,
            eficiencia_percentual=80.0,
            pro_labore=2500.0,
            taxa_energia_kwh=0.80
        )
        db.session.add(config)

        # 2. Custos Fixos
        cf1 = CustoFixo(descricao="Aluguel", valor_mensal=800.0)
        cf2 = CustoFixo(descricao="Internet", valor_mensal=120.0)
        cf3 = CustoFixo(descricao="Simples Nacional (DAS MEI)", valor_mensal=80.0)
        cf4 = CustoFixo(descricao="Silhouette Studio e Canva", valor_mensal=80.0)

        # 3. Equipamentos (Depreciação)
        eq1 = Equipamento(nome="Silhouette Cameo 4", potencia_watts=50, valor_aquisicao=2800.0, vida_util_meses=48, valor_residual=600.0)
        eq2 = Equipamento(nome="Epson EcoTank L8050", potencia_watts=100, valor_aquisicao=2800.0, vida_util_meses=36, valor_residual=500.0)

        # 4. Materiais / Insumos
        m1 = Material(nome="Papel Offset A4 180g", unidade_medida="folha", custo_embalagem=25.0, quantidade_embalagem=50.0)
        m2 = Material(nome="Fita de Cetim 38mm", unidade_medida="metro", custo_embalagem=15.0, quantidade_embalagem=10.0)
        m3 = Material(nome="Caixa de Envio Padrão", unidade_medida="unidade", custo_embalagem=100.0, quantidade_embalagem=50.0)

        # 5. Desgastes e Consumíveis Invisíveis
        d1 = Desgaste(nome="Lâmina de Corte Premium", custo=150.0, rendimento_ciclos=500)
        d2 = Desgaste(nome="Base Adesiva de Corte", custo=120.0, rendimento_ciclos=200)

        db.session.add_all([cf1, cf2, cf3, cf4, eq1, eq2, m1, m2, m3, d1, d2])
        db.session.commit()
        
        # Cria clientes e pedidos mockados para o kanban pra não quebrar a tela anterior
        c1 = Cliente(
            nome="João Silva", 
            telefone="11999998888", 
            email="joao@example.com",
            instagram="@joaosilva.festa",
            origem="Instagram",
            data_nascimento="1985-06-15",
            observacoes="Cliente comprou ano passado e agora voltou para renovar o kit festa do filho."
        )
        p1 = Produto(nome="Kit Festa Patrulha (Semente)", tempo_producao_minutos=120, perda_tecnica_percentual=10, preco_venda=180.0)
        db.session.add_all([c1, p1])
        db.session.commit()
        
        from models import ItemPedido
        ped1 = Pedido(cliente_id=c1.id, valor_total=180.0, fase_kanban="Em Produção", descricao_geral="Peça mockada automatica")
        db.session.add(ped1)
        db.session.commit()
        
        item1 = ItemPedido(pedido_id=ped1.id, produto_id=p1.id, nome_item=p1.nome, quantidade=1, valor_unitario=180.0, valor_subtotal=180.0)
        db.session.add(item1)
        db.session.commit()

        print("Banco de dados Avançado Criado com Sucesso!")

if __name__ == "__main__":
    seed_advanced()
