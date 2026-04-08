from database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Usuário') # Administrador, Gerente, Usuário

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    endereco = db.Column(db.Text, nullable=True)
    instagram = db.Column(db.String(100), nullable=True)
    data_nascimento = db.Column(db.String(20), nullable=True) # YYYY-MM-DD
    origem = db.Column(db.String(50), nullable=True) # ex: Instagram, Indicacao, Feira
    observacoes = db.Column(db.Text, nullable=True)
    pedidos = db.relationship('Pedido', backref='cliente', lazy=True)

class ConfiguracaoOperacional(db.Model):
    __tablename__ = 'configuracoes'
    id = db.Column(db.Integer, primary_key=True)
    dias_trabalhados = db.Column(db.Integer, default=22)
    horas_por_dia = db.Column(db.Integer, default=8)
    eficiencia_percentual = db.Column(db.Float, default=80.0) # 80%
    pro_labore = db.Column(db.Float, default=2500.0)
    taxa_energia_kwh = db.Column(db.Float, default=0.80)
    previsao_energia_mensal = db.Column(db.Float, default=0.0)

class CustoFixo(db.Model):
    __tablename__ = 'custos_fixos'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor_mensal = db.Column(db.Float, nullable=False)

class Equipamento(db.Model):
    __tablename__ = 'equipamentos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    potencia_watts = db.Column(db.Float, default=100.0)
    valor_aquisicao = db.Column(db.Float, nullable=False)
    vida_util_meses = db.Column(db.Integer, default=60)
    valor_residual = db.Column(db.Float, default=0)

class Material(db.Model):
    __tablename__ = 'materiais'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    unidade_medida = db.Column(db.String(20), nullable=False)
    custo_embalagem = db.Column(db.Float, nullable=False) # Custo pelo pacote fechado
    quantidade_embalagem = db.Column(db.Float, nullable=False) # Quantas unidades vêm
    # Ex: Folha Offset A4 180g (Pacote 50, Custo 25.0). Custo un: 0.50
    
    link_compra = db.Column(db.String(255), nullable=True)
    quantidade_atual = db.Column(db.Float, default=0.0)
    quantidade_minima = db.Column(db.Float, default=0.0)

class Desgaste(db.Model):
    __tablename__ = 'desgastes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False) # Lâmina, Base
    custo = db.Column(db.Float, nullable=False)
    rendimento_ciclos = db.Column(db.Integer, nullable=False) # Ex: 500 cortes

class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    custo_producao = db.Column(db.Float, default=0) # CUT somado na calculadora
    tempo_producao_minutos = db.Column(db.Integer, default=0)
    perda_tecnica_percentual = db.Column(db.Float, default=10.0)
    
    # Precos finais
    preco_venda = db.Column(db.Float, nullable=False) # Ex-preco_sugerido
    
    itens_vendidos = db.relationship('ItemPedido', backref='produto_base', lazy=True)
    imagens = db.relationship('ProdutoImagem', backref='produto', lazy=True, cascade="all, delete-orphan")

class ProdutoImagem(db.Model):
    __tablename__ = 'produto_imagens'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    caminho = db.Column(db.String(255), nullable=False)

class ProdutoMaterial(db.Model):
    __tablename__ = 'produto_materiais'
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materiais.id'), primary_key=True)
    quantidade_usada = db.Column(db.Float, nullable=False)

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    descricao_geral = db.Column(db.Text, nullable=True) # Observacoes globais
    
    # Orçamento Settings
    forma_pagamento = db.Column(db.String(50), nullable=True)
    validade_dias = db.Column(db.Integer, default=7)
    
    valor_total = db.Column(db.Float, nullable=False)
    fase_kanban = db.Column(db.String(50), default='Primeiro Contato')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    posicao_ordem = db.Column(db.Integer, default=0)
    
    itens = db.relationship('ItemPedido', backref='pedido_pai', lazy=True, cascade="all, delete-orphan")

class ItemPedido(db.Model):
    __tablename__ = 'itens_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=True) # Pode ser NULL se for genérico
    nome_item = db.Column(db.String(150), nullable=False) # Copia o nome do produto no momento da compra
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    valor_unitario = db.Column(db.Float, nullable=False)
    valor_subtotal = db.Column(db.Float, nullable=False)

class ConfiguracaoVisual(db.Model):
    __tablename__ = 'configuracoes_visuais'
    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(100), default="CraftManager")
    logo_path = db.Column(db.String(255), nullable=True)
    favicon_path = db.Column(db.String(255), nullable=True)
    cor_primaria = db.Column(db.String(10), default="#6366f1")
    cor_secundaria = db.Column(db.String(10), default="#8b5cf6")
    cor_fundo = db.Column(db.String(10), default="#0f172a")
    fonte_principal = db.Column(db.String(50), default="Outfit")
