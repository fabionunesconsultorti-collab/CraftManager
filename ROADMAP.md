# 🚀 Roadmap CraftManager (Planejamento de Futuro)

Este documento foi criado para registrar ideias, projetos futuros e potenciais evoluções arquiteturais para a plataforma, guiando o desenvolvimento gradativo para transformá-la no motor central da gestão produtiva e financeira do ateliê.

---

## 🎯 Fase 1: Inteligência e Controle Operacional

Essas implementações visam remover o trabalho manual repetitivo (dupla digitação de estoque, esquecimentos de datas) de dentro do negócio fechando lacunas no fluxo.

- [ ] **Integração de Estoque na Ordem de Produção (Baixa Automática)**
  * **Objetivo:** O sistema ler os insumos vinculados ao arquivo do Produto salvo e abater exatamente as porcentagens/unidades do inventário (tela de materiais) na medida em que os cartões avançam pelo Kanban.
  * **Status Técnico:** Banco de dados já preparado (a Calculadora já salva e indexa custo). Falta unificar a lógica na rota de avanço do Kanban.
- [ ] **Calendário Visual de Prazos (Agenda de Lançamentos)**
  * **Objetivo:** Visualização de todos os pedidos da casa atrelados a suas "Datas do Evento/Festa" usando uma interface de formato mensal.
  * **Status Técnico:** Exigirá a adição do campo `data_evento` ou `previsao_entrega` no modelo do Banco de Dados do Pedido, além de uma nova rota com biblioteca (ex: FullCalendar).

---

## 📢 Fase 2: Módulos de Interface Cliente

Foco em criar canais onde o sistema facilite vendas passivas, comunicando o portfólio já existente sem exigir que você atenda no um-a-um desde o começo.

- [ ] **Catálogo / Cardápio Digital Público**
  * **Objetivo:** Construir uma página estática externa, limpa (estilo "Menu Digital" para smartphone). Ela será apenas um espelho de leitura (Read-Only) da tela atual de Portfólio de Produtos (com a foto de layout galeria).
  * **Integração:** Adicionar link de redirecionamento para o seu WhatsApp corporativo pré-preenchido: *"Olá equipe, encontrei o item X de valor Y no seu catálogo e gostaria de alinhar um pedido..."*.
- [ ] **Avisos Automatizados Integrados no Kanban**
  * **Objetivo:** Botão de "Notificar Via Whats" integrado na tela da Gerência de Pedidos, usando links API de Web-WhatsApp para informar: *"Seu pedido está em produção"*, *"A arte está pronta para aprovação"* ou *"Pronto para retirada!"*.

---

## 📈 Fase 3: Maturidade de Negócio e Fechamento de Caixa

Nesta fase a plataforma adquire os "poderes" do fluxo financeiro macro, transformando-se oficialmente num mini-ERP gerencial robusto.

- [ ] **Módulo de Fluxo de Caixa (Dashboard Financeiro)**
  * **Objetivo:** Diferenciar o cálculo do "Preço/Tributos" de uma ferramenta real de caixa. Adição de "Receitas Adquiridas (Vendas Finalizadas)" contra "Despesas Adquiridas (Pagamentos a Fornecedores, Papelaria Fixa, Energia, Internet)".
- [ ] **Relatório de Curva ABC & B.I.**
  * **Objetivo:** Adicionar relatórios de final de mês que analisam: Qual produto vendeu mais no seu volume total versus qual gerou mais impacto logístico. Qual cliente comprou mais nos últimos 6 meses (Ranking Vip).
  * **Status Técnico:** Consolidar painéis chart.js na homepage unindo queries na base de Clientes, Pedidos e Materiais.

---
> [!TIP]
> **Como utilizar este documento:** Arquivo livre! Sinta-se à vontade para reordená-lo, apagar o que achar irrelevante ou continuar acrescentando suas ideias do dia-a-dia para guiar nosso pareamento futuro quando novos ciclos de melhoria se abrirem.
