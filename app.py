from flask import Flask, render_template, request, jsonify
from database import db
from models import Cliente, Material, CustoFixo, Produto, Pedido, ConfiguracaoOperacional, Equipamento, Desgaste, ProdutoMaterial, ProdutoImagem
import os
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gerencia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads/produtos')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)

# Rotas Web (Frontend)
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/novo-pedido')
def novo_pedido():
    return render_template('novo_pedido.html')

@app.route('/orcamento/<int:pedido_id>')
def visualizar_orcamento(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    return render_template('orcamento.html', pedido=pedido)

@app.route('/kanban')
def kanban():
    return render_template('kanban.html')

@app.route('/pedidos')
def gerenciar_pedidos():
    return render_template('pedidos.html')

@app.route('/recibo/<int:pedido_id>')
def visualizar_recibo(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    return render_template('recibo.html', pedido=pedido)

@app.route('/clientes')
def gerenciar_clientes():
    return render_template('clientes.html')

@app.route('/produtos')
def gerenciar_produtos():
    return render_template('produtos.html')

@app.route('/engenharia-custos')
def engenharia_custos():
    return render_template('engenharia.html')

@app.route('/equipamentos')
def gerenciar_equipamentos():
    return render_template('equipamentos.html')

@app.route('/calculadora-produto')
def calculadora_produto():
    return render_template('calculadora.html')

@app.route('/materiais')
def gerenciar_materiais():
    return render_template('materiais.html')

# Rotas API (Para uso dinamico com JS)
@app.route('/api/engenharia/vht', methods=['GET'])
def calcular_vht():
    # 1. Busca configurações essenciais
    config = ConfiguracaoOperacional.query.first()
    if not config:
        return jsonify({"erro": "Configure os parâmetros operacionais primeiro"}), 400
        
    # 2. Despesas Fixas e Depreciação
    despesas_fixas = sum([c.valor_mensal for c in CustoFixo.query.all()])
    equipamentos = Equipamento.query.all()
    depreciacao_mensal = sum([(e.valor_aquisicao - e.valor_residual) / e.vida_util_meses if e.vida_util_meses else 0 for e in equipamentos])
    
    total_custos_mes = despesas_fixas + config.pro_labore + depreciacao_mensal
    
    # 3. Horas Produtivas
    horas_mes = config.dias_trabalhados * config.horas_por_dia
    horas_produtivas = horas_mes * (config.eficiencia_percentual / 100.0)
    
    vht = total_custos_mes / horas_produtivas if horas_produtivas > 0 else 0
    
    return jsonify({
        "vht_calculado": round(vht, 2),
        "total_depreciacao": round(depreciacao_mensal, 2),
        "total_fixo": round(despesas_fixas + config.pro_labore, 2),
        "horas_produtivas": round(horas_produtivas, 2)
    })

# Rota Equipamentos CRUD
@app.route('/api/equipamentos', methods=['GET', 'POST'])
def api_equipamentos():
    if request.method == 'GET':
        eqs = Equipamento.query.all()
        return jsonify([{"id": e.id, "nome": e.nome, "aquisicao": e.valor_aquisicao, "vida_util": e.vida_util_meses, "residual": e.valor_residual, "depreciacao_mensal": (e.valor_aquisicao - e.valor_residual) / e.vida_util_meses if e.vida_util_meses else 0} for e in eqs])
    else:
        data = request.json
        e = Equipamento(
            nome=data['nome'],
            valor_aquisicao=float(data['valor_aquisicao']),
            vida_util_meses=int(data['vida_util_meses']),
            valor_residual=float(data['valor_residual'])
        )
        db.session.add(e)
        db.session.commit()
        return jsonify({"status": "success"})

@app.route('/api/equipamentos/<int:eq_id>', methods=['DELETE'])
def del_equipamento(eq_id):
    e = Equipamento.query.get_or_404(eq_id)
    db.session.delete(e)
    db.session.commit()
    return jsonify({"status": "success"})

# Rota para carregar informações necessárias para calculadora
@app.route('/api/catalogo_calculos', methods=['GET'])
def catalogo_calculos():
    materiais = [{"id": m.id, "nome": m.nome, "custo_unidade": (m.custo_embalagem / m.quantidade_embalagem) if m.quantidade_embalagem else 0, "custo_embalagem": m.custo_embalagem, "quantidade_embalagem": m.quantidade_embalagem, "unidade": m.unidade_medida, "link_compra": m.link_compra, "quantidade_minima": m.quantidade_minima, "quantidade_atual": m.quantidade_atual} for m in Material.query.all()]
    desgastes = [{"id": d.id, "nome": d.nome, "custo_ciclo": (d.custo / d.rendimento_ciclos) if d.rendimento_ciclos else 0, "custo": d.custo, "rendimento": d.rendimento_ciclos} for d in Desgaste.query.all()]
    return jsonify({"materiais": materiais, "desgastes": desgastes})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp'}

@app.route('/api/produtos', methods=['GET', 'POST'])
def handle_produtos():
    if request.method == 'GET':
        prods = Produto.query.all()
        resultado = []
        for p in prods:
            imgs = [i.caminho for i in p.imagens]
            img_capa = imgs[0] if imgs else None
            resultado.append({
                "id": p.id, 
                "nome": p.nome,
                "tempo_producao_minutos": p.tempo_producao_minutos,
                "preco_venda": p.preco_venda,
                "imagem_capa": img_capa,
                "todas_imagens": imgs
            })
        return jsonify(resultado)
    else:
        # Puxando como request.form pois virou FormData para suporte a arquivo
        nome = request.form.get('nome')
        custo_producao = request.form.get('custo_producao', 0)
        tempo_producao = request.form.get('tempo_producao_minutos', 0)
        perda = request.form.get('perda_tecnica_percentual', 0)
        preco = request.form.get('preco_venda', 0)
        
        p = Produto(
            nome=nome,
            custo_producao=float(custo_producao),
            tempo_producao_minutos=int(tempo_producao),
            perda_tecnica_percentual=float(perda),
            preco_venda=float(preco)
        )
        db.session.add(p)
        db.session.commit()
        
        # Lida com o Upload de Fotos
        files = request.files.getlist('imagens')
        for file in files:
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_name = f"{p.id}_{filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(save_path)
                
                # Salva o link no DB
                img_record = ProdutoImagem(produto_id=p.id, caminho=unique_name)
                db.session.add(img_record)
        
        db.session.commit()
        return jsonify({"status": "success", "id": p.id})

@app.route('/api/produtos/<int:prod_id>', methods=['DELETE'])
def del_produto(prod_id):
    p = Produto.query.get_or_404(prod_id)
    # Deleta arquivos fisicos do disco
    for img in p.imagens:
        caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], img.caminho)
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)
            
    db.session.delete(p)
    db.session.commit()
    return jsonify({"status": "deleted"})

# API CRUDS Clientes e Histórico
@app.route('/api/clientes', methods=['GET', 'POST'])
def api_clientes():
    if request.method == 'GET':
        resultado = []
        for c in Cliente.query.all():
            hist_pedidos = []
            for p in c.pedidos:
                # Retorna só o nome do produto caso exista, fallback pro custom
                p_nome = p.produto.nome if p.produto else "Personalizado Avulso"
                hist_pedidos.append({
                    "id": p.id,
                    "produto": p_nome,
                    "valor_total": p.valor_total,
                    "fase": p.fase_kanban,
                    "data": p.data_criacao.strftime('%d/%m/%Y')
                })
                
            resultado.append({
                "id": c.id, "nome": c.nome, "telefone": c.telefone, "email": c.email,
                "endereco": c.endereco, "instagram": c.instagram, 
                "data_nascimento": c.data_nascimento, "origem": c.origem,
                "observacoes": c.observacoes, "historico_pedidos": hist_pedidos
            })
        return jsonify(resultado)
    else:
        # Criacao de cliente novo
        data = request.json
        c = Cliente(
            nome=data.get('nome'),
            telefone=data.get('telefone'),
            email=data.get('email'),
            endereco=data.get('endereco'),
            instagram=data.get('instagram'),
            data_nascimento=data.get('data_nascimento'),
            origem=data.get('origem'),
            observacoes=data.get('observacoes')
        )
        db.session.add(c)
        db.session.commit()
        return jsonify({"status": "success", "id": c.id})

@app.route('/api/clientes/<int:item_id>', methods=['DELETE'])
def del_cliente(item_id):
    c = Cliente.query.get_or_404(item_id)
    # Impede deleção se tiver pedidos
    if c.pedidos:
        return jsonify({"status": "error", "message": "Este cliente possui histórico financeiro."}), 400
    db.session.delete(c)
    db.session.commit()
    return jsonify({"status": "deleted"})

# API CRUDS Materiais e Desgastes
@app.route('/api/materiais', methods=['POST'])
def add_material():
    data = request.json
    m = Material(
        nome=data['nome'],
        unidade_medida=data['unidade_medida'],
        custo_embalagem=float(data['custo_embalagem']),
        quantidade_embalagem=float(data['quantidade_embalagem']),
        link_compra=data.get('link_compra', ''),
        quantidade_atual=float(data.get('quantidade_atual', 0.0)),
        quantidade_minima=float(data.get('quantidade_minima', 0.0))
    )
    db.session.add(m)
    db.session.commit()
    return jsonify({"status": "success", "id": m.id})

@app.route('/api/materiais/<int:item_id>', methods=['DELETE'])
def del_material(item_id):
    m = Material.query.get_or_404(item_id)
    db.session.delete(m)
    db.session.commit()
    return jsonify({"status": "deleted"})

@app.route('/api/materiais/<int:item_id>/estoque', methods=['POST'])
def update_estoque_material(item_id):
    m = Material.query.get_or_404(item_id)
    data = request.json
    acao = data.get('acao')
    quantidade = float(data.get('quantidade', 1.0))
    
    if acao == 'adicionar':
        m.quantidade_atual += quantidade
    elif acao == 'reduzir':
        m.quantidade_atual -= quantidade
        if m.quantidade_atual < 0:
            m.quantidade_atual = 0.0
    
    db.session.commit()
    return jsonify({"status": "success", "quantidade_atual": m.quantidade_atual})

@app.route('/api/desgastes', methods=['POST'])
def add_desgaste():
    data = request.json
    d = Desgaste(
        nome=data['nome'],
        custo=float(data['custo']),
        rendimento_ciclos=int(data['rendimento_ciclos'])
    )
    db.session.add(d)
    db.session.commit()
    return jsonify({"status": "success", "id": d.id})

@app.route('/api/desgastes/<int:item_id>', methods=['DELETE'])
def del_desgaste(item_id):
    d = Desgaste.query.get_or_404(item_id)
    db.session.delete(d)
    db.session.commit()
    return jsonify({"status": "deleted"})
# API KANBAN / PEDIDOS
@app.route('/api/pedidos', methods=['GET', 'POST'])
def handle_pedidos():
    if request.method == 'GET':
        pedidos = Pedido.query.all()
        result = []
        for p in pedidos:
            cliente = p.cliente
            # Montar a UI do Kanban: Se tiver apenas 1 item mostra o nome, se tiver + mostra "Pacote de X itens"
            if p.itens:
                if len(p.itens) == 1:
                    produto_nome = f"{p.itens[0].quantidade}x {p.itens[0].nome_item}"
                else:
                    produto_nome = f"Pacote Múltiplo ({len(p.itens)} itens)"
            else:
                produto_nome = "Pedido Vazio"
                
            result.append({
                'id': p.id,
                'cliente_nome': cliente.nome if cliente else 'S/N',
                'cliente_telefone': cliente.telefone if cliente else '',
                'produto_nome': produto_nome,
                'descricao': p.descricao_geral,
                'valor_total': p.valor_total,
                'fase_kanban': p.fase_kanban,
                'posicao_ordem': p.posicao_ordem,
                'data_criacao': p.data_criacao.strftime('%d/%m/%Y'),
                'forma_pagamento': p.forma_pagamento
            })
        return jsonify(result)
    else:
        data = request.json
        
        # Logica para Cliente Novo ou Existente
        if data.get('cliente_modo') == 'novo':
            cli = Cliente(
                nome=data.get('cliente_nome'),
                telefone=data.get('cliente_telefone'),
                origem='Novo Pedido Direto'
            )
            db.session.add(cli)
            db.session.commit()
            cli_id = cli.id
        else:
            cli_id = data.get('cliente_id')
            if not cli_id:
                return jsonify({"error": "Cliente existente não selecionado"}), 400

        # Processar Itens
        itens_data = data.get('itens', [])
        valor_final_calculado = sum(float(item['subtotal']) for item in itens_data)
        
        # Criação do Pedido "Pai"
        novo_pedido = Pedido(
            cliente_id=cli_id,
            descricao_geral=data.get('descricao'),
            valor_total=valor_final_calculado,
            fase_kanban=data.get('fase_kanban', 'Novo Pedido'),
            forma_pagamento=data.get('forma_pagamento', 'A Combinar'),
            validade_dias=int(data.get('validade_dias', 7))
        )
        db.session.add(novo_pedido)
        db.session.commit()
        
        # Inserção dos Filhos (Carrinho)
        from models import ItemPedido
        for item in itens_data:
            novo_item = ItemPedido(
                pedido_id=novo_pedido.id,
                produto_id=item.get('produto_id') if item.get('produto_id') else None,
                nome_item=item.get('nome_item'),
                quantidade=int(item.get('quantidade', 1)),
                valor_unitario=float(item.get('valor_unitario')),
                valor_subtotal=float(item.get('subtotal'))
            )
            db.session.add(novo_item)
            
        db.session.commit()
        
        return jsonify({"status": "success", "pedido_id": novo_pedido.id})

@app.route('/api/pedidos/<int:pedido_id>', methods=['DELETE', 'PUT'])
def gerenciar_pedido_individual(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if request.method == 'DELETE':
        db.session.delete(pedido)
        db.session.commit()
        return jsonify({"status": "deleted"})
    elif request.method == 'PUT':
        data = request.json
        if 'fase_kanban' in data:
            pedido.fase_kanban = data['fase_kanban']
        if 'forma_pagamento' in data:
            pedido.forma_pagamento = data['forma_pagamento']
        if 'descricao_geral' in data:
            pedido.descricao_geral = data['descricao_geral']
        db.session.commit()
        return jsonify({"status": "updated"})

@app.route('/api/pedidos/<int:pedido_id>/fase', methods=['POST'])
def atualizar_fase_pedido(pedido_id):
    data = request.json
    pedido = Pedido.query.get_or_404(pedido_id)
    if 'fase_kanban' in data:
        pedido.fase_kanban = data['fase_kanban']
    db.session.commit()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True, port=5000)
