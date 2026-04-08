from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from database import db
from models import Cliente, Material, CustoFixo, Produto, Pedido, ConfiguracaoOperacional, Equipamento, Desgaste, ProdutoMaterial, ProdutoImagem, Usuario, ConfiguracaoVisual
import os
import zipfile
import io
import shutil
import tempfile
import subprocess
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'craftmanager_secret_super_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gerencia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads/produtos')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)

# Injeção global de configurações visuais em todos os templates
@app.context_processor
def inject_visual_config():
    config = ConfiguracaoVisual.query.first()
    if not config:
        config = ConfiguracaoVisual()
        db.session.add(config)
        db.session.commit()
    return dict(visual_config=config)

IDENTIDADE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads/identidade')
os.makedirs(IDENTIDADE_FOLDER, exist_ok=True)
app.config['IDENTIDADE_FOLDER'] = IDENTIDADE_FOLDER

def role_required(min_level):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login', next=request.url))
            
            user_role = session.get('role', 'Usuário')
            role_map = {'Usuário': 1, 'Gerente': 2, 'Administrador': 3}
            current_level = role_map.get(user_role, 1)
            
            if current_level < min_level:
                if request.path.startswith('/api/'):
                    return jsonify({"erro": "Acesso negado para o seu perfil."}), 403
                return render_template('dashboard.html', erro_acesso="Acesso negado para o seu nível hierárquico.")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Usuario.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', erro="Credenciais inválidas")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Rotas Web (Frontend)
@app.route('/')
@role_required(1)
def dashboard():
    return render_template('dashboard.html')

@app.route('/novo-pedido')
@role_required(1)
def novo_pedido():
    return render_template('novo_pedido.html')

@app.route('/orcamento/<int:pedido_id>')
@role_required(1)
def visualizar_orcamento(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    return render_template('orcamento.html', pedido=pedido)

@app.route('/kanban')
@role_required(1)
def kanban():
    return render_template('kanban.html')

@app.route('/pedidos')
@role_required(1)
def gerenciar_pedidos():
    return render_template('pedidos.html')

@app.route('/recibo/<int:pedido_id>')
@role_required(1)
def visualizar_recibo(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    return render_template('recibo.html', pedido=pedido)

@app.route('/clientes')
@role_required(1)
def gerenciar_clientes():
    return render_template('clientes.html')

@app.route('/produtos')
@role_required(2)
def gerenciar_produtos():
    return render_template('produtos.html')

@app.route('/engenharia-custos')
@role_required(3)
def engenharia_custos():
    return render_template('engenharia.html')

@app.route('/equipamentos')
@role_required(2)
def gerenciar_equipamentos():
    return render_template('equipamentos.html')

@app.route('/calculadora-produto')
@role_required(2)
def calculadora_produto():
    return render_template('calculadora.html')

@app.route('/materiais')
@role_required(2)
def gerenciar_materiais():
    return render_template('materiais.html')

@app.route('/manutencao')
@role_required(3)
def manutencao():
    return render_template('manutencao.html')

# Rotas API Manutenção / Backup
@app.route('/api/backup/download', methods=['GET'])
@role_required(3)
def download_backup():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Salvando o banco de dados
        db_path = os.path.join(app.instance_path, 'gerencia.db')
        if os.path.exists(db_path):
            zf.write(db_path, 'gerencia.db')
            
        # Salvando as imagens (se existirem)
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('uploads', os.path.relpath(file_path, app.config['UPLOAD_FOLDER']))
                    zf.write(file_path, arcname)
                    
    memory_file.seek(0)
    data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(memory_file, download_name=f'backup_craftmanager_{data_hora}.zip', as_attachment=True)

@app.route('/api/backup/restore', methods=['POST'])
@role_required(3)
def restore_backup():
    if 'backup_file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
        
    file = request.files['backup_file']
    if file.filename == '':
        return jsonify({"erro": "Arquivo não selecionado"}), 400
        
    if not file.filename.endswith('.zip'):
        return jsonify({"erro": "O arquivo deve ter extensão .zip"}), 400
        
    try:
        temp_dir = tempfile.mkdtemp()
        temp_zip_path = os.path.join(temp_dir, 'backup.zip')
        file.save(temp_zip_path)
        
        with zipfile.ZipFile(temp_zip_path, 'r') as zf:
            zf.extractall(temp_dir)
            
        # Restaura Database
        extracted_db = os.path.join(temp_dir, 'gerencia.db')
        if os.path.exists(extracted_db):
            os.makedirs(app.instance_path, exist_ok=True)
            db_dest = os.path.join(app.instance_path, 'gerencia.db')
            shutil.copy2(extracted_db, db_dest)
            
        # Restaura Imagens
        extracted_uploads = os.path.join(temp_dir, 'uploads')
        if os.path.exists(extracted_uploads):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            for item in os.listdir(extracted_uploads):
                s = os.path.join(extracted_uploads, item)
                d = os.path.join(app.config['UPLOAD_FOLDER'], item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
                    
        shutil.rmtree(temp_dir)
        return jsonify({"status": "success", "mensagem": "Sistema restaurado com sucesso!"})
    except Exception as e:
        return jsonify({"erro": f"Erro interno ao restaurar: {str(e)}"}), 500

@app.route('/api/backup/update-system', methods=['POST'])
@role_required(3)
def update_system_git():
    try:
        # Comando para baixar a versao da main invisivelmente
        result = subprocess.run(['git', 'pull', 'origin', 'main'], capture_output=True, text=True, cwd=app.root_path)
        
        if result.returncode == 0:
            return jsonify({"status": "success", "mensagem": "Aplicativo sincronizado e atualizado via Git!", "log": result.stdout})
        else:
            return jsonify({"erro": f"Git retornou código de falha ({result.returncode})", "log": result.stderr}), 500
    except Exception as e:
        return jsonify({"erro": f"Falha de comunicação OS terminal: {str(e)}"}), 500

# Rotas API (Para uso dinamico com JS)
@app.route('/api/engenharia/vht', methods=['GET'])
@role_required(3)
def calcular_vht():
    # 1. Busca configurações essenciais
    config = ConfiguracaoOperacional.query.first()
    if not config:
        return jsonify({"erro": "Configure os parâmetros operacionais primeiro"}), 400
        
    # 2. Despesas Fixas e Depreciação
    despesas_fixas = sum([c.valor_mensal for c in CustoFixo.query.all()])
    equipamentos = Equipamento.query.all()
    depreciacao_mensal = sum([(e.valor_aquisicao - e.valor_residual) / e.vida_util_meses if e.vida_util_meses else 0 for e in equipamentos])
    
    total_custos_mes = despesas_fixas + config.pro_labore + depreciacao_mensal + (config.previsao_energia_mensal or 0)
    
    # 3. Horas Produtivas
    horas_mes = config.dias_trabalhados * config.horas_por_dia
    horas_produtivas = horas_mes * (config.eficiencia_percentual / 100.0)
    
    vht = total_custos_mes / horas_produtivas if horas_produtivas > 0 else 0
    
    return jsonify({
        "vht_calculado": round(vht, 2),
        "total_depreciacao": round(depreciacao_mensal, 2),
        "total_fixo": round(despesas_fixas + config.pro_labore + (config.previsao_energia_mensal or 0), 2),
        "horas_produtivas": round(horas_produtivas, 2)
    })

# Rotas de Gestão de Usuários
@app.route('/api/usuarios', methods=['GET', 'POST'])
@role_required(3)
def api_usuarios():
    if request.method == 'GET':
        users = Usuario.query.all()
        return jsonify([{"id": u.id, "username": u.username, "role": u.role} for u in users])
    else:
        data = request.json
        if Usuario.query.filter_by(username=data['username']).first():
            return jsonify({"erro": "Usuário já existe"}), 400
        
        user = Usuario(username=data['username'], role=data['role'])
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        return jsonify({"status": "success"})

@app.route('/api/usuarios/<int:user_id>', methods=['DELETE'])
@role_required(3)
def del_usuario(user_id):
    if user_id == session.get('user_id'):
        return jsonify({"erro": "Você não pode excluir a si mesmo"}), 400
    user = Usuario.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/usuarios/<int:user_id>/reset-password', methods=['POST'])
@role_required(3)
def reset_password(user_id):
    data = request.json
    user = Usuario.query.get_or_404(user_id)
    user.set_password(data['new_password'])
    db.session.commit()
    return jsonify({"status": "success"})

# Rotas de Configurações do Negócio
@app.route('/api/configuracoes', methods=['GET'])
@role_required(2)
def get_configuracoes():
    config = ConfiguracaoOperacional.query.first()
    custos_fixos = CustoFixo.query.all()
    
    if not config:
        config = ConfiguracaoOperacional()
        db.session.add(config)
        db.session.commit()

    return jsonify({
        "operacional": {
            "dias_trabalhados": config.dias_trabalhados,
            "horas_por_dia": config.horas_por_dia,
            "eficiencia_percentual": config.eficiencia_percentual,
            "pro_labore": config.pro_labore,
            "previsao_energia_mensal": config.previsao_energia_mensal
        },
        "custos_fixos": [{"id": c.id, "descricao": c.descricao, "valor_mensal": c.valor_mensal} for c in custos_fixos]
    })

@app.route('/api/configuracoes/operacional', methods=['POST'])
@role_required(3)
def update_config_operacional():
    data = request.json
    config = ConfiguracaoOperacional.query.first()
    if not config:
        config = ConfiguracaoOperacional()
        db.session.add(config)
    
    config.dias_trabalhados = int(data.get('dias_trabalhados', 22))
    config.horas_por_dia = int(data.get('horas_por_dia', 8))
    config.eficiencia_percentual = float(data.get('eficiencia_percentual', 80.0))
    config.pro_labore = float(data.get('pro_labore', 2500.0))
    config.previsao_energia_mensal = float(data.get('previsao_energia_mensal', 0.0))
    
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/configuracoes/custo-fixo', methods=['POST'])
@role_required(3)
def add_custo_fixo():
    data = request.json
    novo_custo = CustoFixo(
        descricao=data['descricao'],
        valor_mensal=float(data['valor_mensal'])
    )
    db.session.add(novo_custo)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/configuracoes/custo-fixo/<int:custo_id>', methods=['DELETE'])
@role_required(3)
def del_custo_fixo(custo_id):
    custo = CustoFixo.query.get_or_404(custo_id)
    db.session.delete(custo)
    db.session.commit()
    return jsonify({"status": "success"})

# Rotas de Identidade Visual
@app.route('/api/configuracoes/visual', methods=['GET', 'POST'])
@role_required(2)
def handle_config_visual():
    config = ConfiguracaoVisual.query.first()
    if not config:
        config = ConfiguracaoVisual()
        db.session.add(config)
        db.session.commit()

    if request.method == 'GET':
        return jsonify({
            "nome_empresa": config.nome_empresa,
            "cor_primaria": config.cor_primaria,
            "cor_secundaria": config.cor_secundaria,
            "cor_fundo": config.cor_fundo,
            "fonte_principal": config.fonte_principal,
            "logo_path": config.logo_path,
            "favicon_path": config.favicon_path
        })
    else:
        # Administrador apenas para salvar
        if session.get('role') != 'Administrador':
            return jsonify({"erro": "Apenas administradores podem alterar a identidade visual"}), 403
            
        data = request.json
        config.nome_empresa = data.get('nome_empresa', config.nome_empresa)
        config.cor_primaria = data.get('cor_primaria', config.cor_primaria)
        config.cor_secundaria = data.get('cor_secundaria', config.cor_secundaria)
        config.cor_fundo = data.get('cor_fundo', config.cor_fundo)
        config.fonte_principal = data.get('fonte_principal', config.fonte_principal)
        
        db.session.commit()
        return jsonify({"status": "success"})

@app.route('/api/configuracoes/upload-identidade', methods=['POST'])
@role_required(3)
def upload_identidade():
    config = ConfiguracaoVisual.query.first()
    tipo = request.form.get('tipo') # 'logo' ou 'favicon'
    
    if 'arquivo' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
        
    file = request.files['arquivo']
    if file.filename == '':
        return jsonify({"erro": "Arquivo não selecionado"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Prefixo para evitar conflitos e manter organizado
        unique_name = f"{tipo}_{filename}"
        save_path = os.path.join(app.config['IDENTIDADE_FOLDER'], unique_name)
        file.save(save_path)
        
        if tipo == 'logo':
            config.logo_path = unique_name
        else:
            config.favicon_path = unique_name
            
        db.session.commit()
        return jsonify({"status": "success", "path": unique_name})
    
    return jsonify({"erro": "Tipo de arquivo não permitido"}), 400

# Rota Equipamentos CRUD
@app.route('/api/equipamentos', methods=['GET', 'POST'])
@role_required(2)
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
@role_required(2)
def del_equipamento(eq_id):
    e = Equipamento.query.get_or_404(eq_id)
    db.session.delete(e)
    db.session.commit()
    return jsonify({"status": "success"})

# Rota para carregar informações necessárias para calculadora
@app.route('/api/catalogo_calculos', methods=['GET'])
@role_required(2)
def catalogo_calculos():
    materiais = [{"id": m.id, "nome": m.nome, "custo_unidade": (m.custo_embalagem / m.quantidade_embalagem) if m.quantidade_embalagem else 0, "custo_embalagem": m.custo_embalagem, "quantidade_embalagem": m.quantidade_embalagem, "unidade": m.unidade_medida, "link_compra": m.link_compra, "quantidade_minima": m.quantidade_minima, "quantidade_atual": m.quantidade_atual} for m in Material.query.all()]
    desgastes = [{"id": d.id, "nome": d.nome, "custo_ciclo": (d.custo / d.rendimento_ciclos) if d.rendimento_ciclos else 0, "custo": d.custo, "rendimento": d.rendimento_ciclos} for d in Desgaste.query.all()]
    return jsonify({"materiais": materiais, "desgastes": desgastes})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp'}

@app.route('/api/produtos', methods=['GET', 'POST'])
@role_required(2)
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
@role_required(1)
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
@role_required(1)
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
@role_required(1)
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
@role_required(2)
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
@role_required(2)
def del_material(item_id):
    m = Material.query.get_or_404(item_id)
    db.session.delete(m)
    db.session.commit()
    return jsonify({"status": "deleted"})

@app.route('/api/materiais/<int:item_id>/estoque', methods=['POST'])
@role_required(2)
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
@role_required(2)
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
@role_required(2)
def del_desgaste(item_id):
    d = Desgaste.query.get_or_404(item_id)
    db.session.delete(d)
    db.session.commit()
    return jsonify({"status": "deleted"})
# API KANBAN / PEDIDOS
@app.route('/api/pedidos', methods=['GET', 'POST'])
@role_required(1)
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
@role_required(1)
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
@role_required(1)
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
        # Cria usuário admin padrão se não existir
        if not Usuario.query.filter_by(username='admin').first():
            admin_user = Usuario(username='admin', role='Administrador')
            admin_user.set_password('admin')
            db.session.add(admin_user)
        # Cria usuário gerente padrão se não existir
        if not Usuario.query.filter_by(username='gerente').first():
            gerente_user = Usuario(username='gerente', role='Gerente')
            gerente_user.set_password('gerente')
            db.session.add(gerente_user)
        # Cria usuário usuário padrão se não existir
        if not Usuario.query.filter_by(username='usuario').first():
            usuario_user = Usuario(username='usuario', role='Usuário')
            usuario_user.set_password('usuario')
            db.session.add(usuario_user)
        db.session.commit()
        print("Contas padrão admin, gerente e usuário criadas (se não existiam).")
        # Se já existia admin, ainda imprime mensagem de criação acima; pode ser ajustado
        
        # Permitindo acesso pela rede local via host '0.0.0.0'
        app.run(host='0.0.0.0', debug=True, port=5000)
