import sqlite3
from banco import obter_conexao
from datetime import datetime, timedelta

def criar_usuario(nome, email, senha, telefone=None, whatsapp=None, tipo='cliente'):
    """Cria um novo usuário"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO usuarios (nome, email, senha, telefone, whatsapp, tipo)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nome, email, senha, telefone, whatsapp, tipo))
            conn.commit()
            usuario_id = cursor.lastrowid
            
            # Se for cliente, criar registro de fidelidade
            if tipo == 'cliente':
                cursor.execute('''
                    INSERT INTO fidelidade (cliente_id)
                    VALUES (?)
                ''', (usuario_id,))
                conn.commit()
            
            return usuario_id
        except sqlite3.IntegrityError:
            return None

def buscar_usuario_por_email(email):
    """Busca usuário pelo email"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nome, email, senha, telefone, whatsapp, foto_perfil, tipo
            FROM usuarios
            WHERE email = ?
        ''', (email,))
        resultado = cursor.fetchone()
        
        if resultado and resultado[7] == 'admin':
            # Para admin, buscar logo da barbearia
            cursor.execute('SELECT logo_url FROM configuracoes LIMIT 1')
            config = cursor.fetchone()
            if config and config[0]:
                # Substituir foto_perfil pela logo
                resultado = list(resultado)
                resultado[6] = config[0]
                resultado = tuple(resultado)
        
        return resultado

def obter_usuario_por_id(usuario_id):
    """Obtém usuário pelo ID"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nome, email, telefone, whatsapp, foto_perfil, tipo
            FROM usuarios
            WHERE id = ?
        ''', (usuario_id,))
        resultado = cursor.fetchone()
        
        if resultado and resultado[6] == 'admin':
            # Para admin, buscar logo da barbearia
            cursor.execute('SELECT logo_url FROM configuracoes LIMIT 1')
            config = cursor.fetchone()
            if config and config[0]:
                # Substituir foto_perfil pela logo
                resultado = list(resultado)
                resultado[5] = config[0]
                resultado = tuple(resultado)
        
        return resultado

def atualizar_perfil_usuario(usuario_id, nome, telefone, whatsapp):
    """Atualiza perfil do usuário"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios
            SET nome = ?, telefone = ?, whatsapp = ?
            WHERE id = ?
        ''', (nome, telefone, whatsapp, usuario_id))
        conn.commit()

def atualizar_foto_perfil(usuario_id, foto_perfil):
    """Atualiza foto de perfil do usuário"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE usuarios
            SET foto_perfil = ?
            WHERE id = ?
        ''', (foto_perfil, usuario_id))
        conn.commit()

def atualizar_usuario_completo(usuario_id, nome, telefone, whatsapp, foto_perfil=None):
    """Atualiza dados completos do usuário"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        if foto_perfil:
            cursor.execute('''
                UPDATE usuarios
                SET nome = ?, telefone = ?, whatsapp = ?, foto_perfil = ?
                WHERE id = ?
            ''', (nome, telefone, whatsapp, foto_perfil, usuario_id))
        else:
            cursor.execute('''
                UPDATE usuarios
                SET nome = ?, telefone = ?, whatsapp = ?
                WHERE id = ?
            ''', (nome, telefone, whatsapp, usuario_id))
        conn.commit()

def criar_funcionario(usuario_id, valor_corte, tipo_pagamento):
    """Cria um novo funcionário"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO funcionarios (usuario_id, valor_corte, tipo_pagamento)
            VALUES (?, ?, ?)
        ''', (usuario_id, valor_corte, tipo_pagamento))
        conn.commit()
        return cursor.lastrowid

def listar_funcionarios():
    """Lista todos os funcionários ativos"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.id, u.nome, f.valor_corte, f.tipo_pagamento, u.whatsapp, u.foto_perfil
            FROM funcionarios f
            JOIN usuarios u ON f.usuario_id = u.id
            WHERE f.ativo = 1
        ''')
        return cursor.fetchall()

def listar_funcionarios_detalhado():
    """Lista funcionários com informações detalhadas"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.id, u.nome, u.email, u.telefone, u.whatsapp, f.valor_corte, f.tipo_pagamento, f.ativo, u.foto_perfil
            FROM funcionarios f
            JOIN usuarios u ON f.usuario_id = u.id
        ''')
        return cursor.fetchall()

def obter_funcionario_por_usuario(usuario_id):
    """Obtém ID do funcionário pelo ID do usuário"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM funcionarios WHERE usuario_id = ?
        ''', (usuario_id,))
        resultado = cursor.fetchone()
        return resultado[0] if resultado else None

def listar_servicos():
    """Lista todos os serviços ativos"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nome, preco, duracao
            FROM servicos
            WHERE ativo = 1
        ''')
        return cursor.fetchall()

def verificar_horario_disponivel(funcionario_id, data_hora):
    """Verifica se um horário está disponível para um funcionário"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*)
            FROM agendamentos
            WHERE funcionario_id = ? 
            AND data_hora = ? 
            AND status IN ('pendente', 'aguardando_confirmacao', 'confirmado')
        ''', (funcionario_id, data_hora))
        return cursor.fetchone()[0] == 0

def obter_horarios_ocupados(funcionario_id, data):
    """Obtém horários ocupados de um funcionário em uma data específica"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT strftime('%H:%M', data_hora) as horario
            FROM agendamentos
            WHERE funcionario_id = ? 
            AND date(data_hora) = ?
            AND status IN ('pendente', 'aguardando_confirmacao', 'confirmado')
        ''', (funcionario_id, data))
        return [row[0] for row in cursor.fetchall()]

def criar_agendamento(cliente_id, funcionario_id, servico_id, data_hora, usar_corte_gratuito=False):
    """Cria um novo agendamento"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        
        # Verificar novamente se horário está disponível
        if not verificar_horario_disponivel(funcionario_id, data_hora):
            return None
        
        # Buscar preço do serviço
        cursor.execute('SELECT preco FROM servicos WHERE id = ?', (servico_id,))
        resultado = cursor.fetchone()
        if not resultado:
            return None
        
        preco = resultado[0]
        
        # Se usar corte gratuito, verificar se cliente tem disponível
        if usar_corte_gratuito:
            cursor.execute('''
                SELECT id, cliente_id, cortes_realizados, cortes_gratuitos_disponiveis
                FROM fidelidade
                WHERE cliente_id = ?
            ''', (cliente_id,))
            fidelidade = cursor.fetchone()
            
            if fidelidade and fidelidade[3] > 0:  # cortes_gratuitos_disponiveis
                preco = 0.00
                # Decrementar corte gratuito
                cursor.execute('''
                    UPDATE fidelidade 
                    SET cortes_gratuitos_disponiveis = cortes_gratuitos_disponiveis - 1,
                        data_ultima_atualizacao = CURRENT_TIMESTAMP
                    WHERE cliente_id = ?
                ''', (cliente_id,))
            else:
                return None  # Cliente não tem cortes gratuitos disponíveis
        
        cursor.execute('''
            INSERT INTO agendamentos (cliente_id, funcionario_id, servico_id, data_hora, valor)
            VALUES (?, ?, ?, ?, ?)
        ''', (cliente_id, funcionario_id, servico_id, data_hora, preco))
        conn.commit()
        return cursor.lastrowid

def obter_agendamento_completo(agendamento_id):
    """Obtém detalhes completos de um agendamento"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.cliente_id, u.nome as cliente, u.telefone as cliente_telefone,
                   u.whatsapp as cliente_whatsapp, a.funcionario_id, 
                   uf.nome as funcionario, s.nome as servico,
                   a.data_hora, a.status, a.valor
            FROM agendamentos a
            JOIN usuarios u ON a.cliente_id = u.id
            JOIN funcionarios f ON a.funcionario_id = f.id
            JOIN usuarios uf ON f.usuario_id = uf.id
            JOIN servicos s ON a.servico_id = s.id
            WHERE a.id = ?
        ''', (agendamento_id,))
        return cursor.fetchone()

def listar_agendamentos_cliente(cliente_id):
    """Lista agendamentos de um cliente"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, uf.nome as funcionario, s.nome as servico,
                   datetime(a.data_hora, 'localtime') as data_hora_formatada, 
                   a.status, a.valor
            FROM agendamentos a
            JOIN funcionarios f ON a.funcionario_id = f.id
            JOIN usuarios uf ON f.usuario_id = uf.id
            JOIN servicos s ON a.servico_id = s.id
            WHERE a.cliente_id = ?
            ORDER BY a.data_hora DESC
        ''', (cliente_id,))
        return cursor.fetchall()

def listar_agendamentos_funcionario(funcionario_id, data_filtro=None):
    """Lista agendamentos de um funcionário com filtro opcional de data"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        
        if data_filtro:
            cursor.execute('''
                SELECT a.id, u.nome as cliente, u.telefone, u.whatsapp, s.nome as servico,
                       strftime('%d/%m/%Y às %H:%M', a.data_hora) as data_hora_formatada, 
                       a.status, a.valor, a.data_hora
                FROM agendamentos a
                JOIN usuarios u ON a.cliente_id = u.id
                JOIN servicos s ON a.servico_id = s.id
                WHERE a.funcionario_id = ? AND date(a.data_hora) = ?
                ORDER BY a.data_hora ASC
            ''', (funcionario_id, data_filtro))
        else:
            cursor.execute('''
                SELECT a.id, u.nome as cliente, u.telefone, u.whatsapp, s.nome as servico,
                       strftime('%d/%m/%Y às %H:%M', a.data_hora) as data_hora_formatada, 
                       a.status, a.valor, a.data_hora
                FROM agendamentos a
                JOIN usuarios u ON a.cliente_id = u.id
                JOIN servicos s ON a.servico_id = s.id
                WHERE a.funcionario_id = ?
                ORDER BY a.data_hora DESC
            ''', (funcionario_id,))
        return cursor.fetchall()

def listar_agendamentos_por_status(status):
    """Lista agendamentos por status"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, u.nome as cliente, u.telefone, u.whatsapp, uf.nome as funcionario, 
                   s.nome as servico, strftime('%d/%m/%Y às %H:%M', a.data_hora) as data_hora_formatada, 
                   a.status, a.valor
            FROM agendamentos a
            JOIN usuarios u ON a.cliente_id = u.id
            JOIN funcionarios f ON a.funcionario_id = f.id
            JOIN usuarios uf ON f.usuario_id = uf.id
            JOIN servicos s ON a.servico_id = s.id
            WHERE a.status = ?
            ORDER BY a.data_hora ASC
        ''', (status,))
        return cursor.fetchall()

def listar_agendamentos_cliente(cliente_id):
    """Lista agendamentos de um cliente"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, uf.nome as funcionario, s.nome as servico,
                   strftime('%d/%m/%Y às %H:%M', a.data_hora) as data_hora_formatada, 
                   a.status, a.valor
            FROM agendamentos a
            JOIN funcionarios f ON a.funcionario_id = f.id
            JOIN usuarios uf ON f.usuario_id = uf.id
            JOIN servicos s ON a.servico_id = s.id
            WHERE a.cliente_id = ?
            ORDER BY a.data_hora DESC
        ''', (cliente_id,))
        return cursor.fetchall()

def atualizar_status_agendamento(agendamento_id, novo_status):
    """Atualiza o status de um agendamento e gerencia fidelidade"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        
        # Buscar dados do agendamento
        cursor.execute('''
            SELECT cliente_id, status FROM agendamentos WHERE id = ?
        ''', (agendamento_id,))
        resultado = cursor.fetchone()
        
        if not resultado:
            return False
        
        cliente_id, status_atual = resultado
        
        # Atualizar status
        cursor.execute('''
            UPDATE agendamentos
            SET status = ?
            WHERE id = ?
        ''', (novo_status, agendamento_id))
        
        # Se mudou para concluído, atualizar fidelidade
        if novo_status == 'concluido' and status_atual != 'concluido':
            # Atualizar fidelidade na mesma transação
            # Buscar fidelidade atual
            cursor.execute('''
                SELECT id, cliente_id, cortes_realizados, cortes_gratuitos_disponiveis
                FROM fidelidade
                WHERE cliente_id = ?
            ''', (cliente_id,))
            fidelidade = cursor.fetchone()
            
            if fidelidade:
                cortes_realizados = fidelidade[2] + 1
                cortes_gratuitos = fidelidade[3]
                
                # A cada 10 cortes, ganha 1 gratuito
                if cortes_realizados % 10 == 0:
                    cortes_gratuitos += 1
                
                cursor.execute('''
                    UPDATE fidelidade
                    SET cortes_realizados = ?, 
                        cortes_gratuitos_disponiveis = ?,
                        data_ultima_atualizacao = CURRENT_TIMESTAMP
                    WHERE cliente_id = ?
                ''', (cortes_realizados, cortes_gratuitos, cliente_id))
            else:
                # Criar registro de fidelidade se não existir
                cursor.execute('''
                    INSERT INTO fidelidade (cliente_id, cortes_realizados)
                    VALUES (?, 1)
                ''', (cliente_id,))
        
        conn.commit()
        return True

def obter_fidelidade_cliente(cliente_id):
    """Obtém dados de fidelidade do cliente"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, cliente_id, cortes_realizados, cortes_gratuitos_disponiveis
            FROM fidelidade
            WHERE cliente_id = ?
        ''', (cliente_id,))
        return cursor.fetchone()

def obter_configuracoes_barbearia():
    """Obtém configurações da barbearia"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT nome_barbearia, logo_url, telefone_contato, whatsapp_contato,
                   endereco, horario_funcionamento, dias_funcionamento, descricao,
                   instagram, facebook
            FROM configuracoes
            LIMIT 1
        ''')
        resultado = cursor.fetchone()
        if resultado:
            return {
                'nome_barbearia': resultado[0],
                'logo_url': resultado[1],
                'telefone_contato': resultado[2],
                'whatsapp_contato': resultado[3],
                'endereco': resultado[4],
                'horario_funcionamento': resultado[5],
                'dias_funcionamento': resultado[6],
                'descricao': resultado[7],
                'instagram': resultado[8],
                'facebook': resultado[9]
            }
        return None

def atualizar_configuracoes_barbearia(nome_barbearia, telefone_contato, whatsapp_contato, 
                                     endereco, horario_funcionamento, dias_funcionamento, 
                                     descricao, instagram=None, facebook=None, logo_url=None):
    """Atualiza configurações da barbearia"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        
        # Verificar se já existe configuração
        cursor.execute('SELECT id FROM configuracoes LIMIT 1')
        existe = cursor.fetchone()
        
        if existe:
            if logo_url:
                cursor.execute('''
                    UPDATE configuracoes 
                    SET nome_barbearia = ?, telefone_contato = ?, whatsapp_contato = ?,
                        endereco = ?, horario_funcionamento = ?, dias_funcionamento = ?,
                        descricao = ?, instagram = ?, facebook = ?, logo_url = ?
                    WHERE id = ?
                ''', (nome_barbearia, telefone_contato, whatsapp_contato, endereco,
                      horario_funcionamento, dias_funcionamento, descricao, instagram,
                      facebook, logo_url, existe[0]))
            else:
                cursor.execute('''
                    UPDATE configuracoes 
                    SET nome_barbearia = ?, telefone_contato = ?, whatsapp_contato = ?,
                        endereco = ?, horario_funcionamento = ?, dias_funcionamento = ?,
                        descricao = ?, instagram = ?, facebook = ?
                    WHERE id = ?
                ''', (nome_barbearia, telefone_contato, whatsapp_contato, endereco,
                      horario_funcionamento, dias_funcionamento, descricao, instagram,
                      facebook, existe[0]))
        else:
            cursor.execute('''
                INSERT INTO configuracoes (nome_barbearia, telefone_contato, whatsapp_contato,
                                         endereco, horario_funcionamento, dias_funcionamento,
                                         descricao, instagram, facebook, logo_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome_barbearia, telefone_contato, whatsapp_contato, endereco,
                  horario_funcionamento, dias_funcionamento, descricao, instagram,
                  facebook, logo_url or '/static/uploads/logo-barbearia.jpg'))
        
        conn.commit()

def editar_cliente(cliente_id, nome, telefone, whatsapp, foto_perfil=None):
    """Edita dados de um cliente (apenas admin)"""
    return atualizar_usuario_completo(cliente_id, nome, telefone, whatsapp, foto_perfil)

def editar_funcionario(funcionario_id, nome, telefone, whatsapp, valor_corte, tipo_pagamento, foto_perfil=None):
    """Edita dados de um funcionário"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        
        # Buscar usuario_id do funcionário
        cursor.execute('SELECT usuario_id FROM funcionarios WHERE id = ?', (funcionario_id,))
        resultado = cursor.fetchone()
        if not resultado:
            return False
        
        usuario_id = resultado[0]
        
        # Atualizar dados do usuário
        atualizar_usuario_completo(usuario_id, nome, telefone, whatsapp, foto_perfil)
        
        # Atualizar dados específicos do funcionário
        cursor.execute('''
            UPDATE funcionarios
            SET valor_corte = ?, tipo_pagamento = ?
            WHERE id = ?
        ''', (valor_corte, tipo_pagamento, funcionario_id))
        
        conn.commit()
        return True

def listar_clientes_detalhado():
    """Lista clientes com informações de fidelidade"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.nome, u.email, u.telefone, u.whatsapp, u.foto_perfil,
                   COALESCE(f.cortes_realizados, 0) as cortes_realizados,
                   COALESCE(f.cortes_gratuitos_disponiveis, 0) as cortes_gratuitos
            FROM usuarios u
            LEFT JOIN fidelidade f ON u.id = f.cliente_id
            WHERE u.tipo = 'cliente'
            ORDER BY u.nome
        ''')
        return cursor.fetchall()

def calcular_valor_funcionario(valor_servico, valor_corte, tipo_pagamento):
    """Calcula o valor que o funcionário recebe baseado no tipo de pagamento"""
    if tipo_pagamento == 'porcentagem':
        return (valor_servico * valor_corte) / 100
    else:  # fixo
        return valor_corte

def obter_estatisticas_admin():
    """Obtém estatísticas para o dashboard do admin"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        
        # Faturamento do mês atual
        cursor.execute('''
            SELECT COALESCE(SUM(valor), 0)
            FROM agendamentos
            WHERE status = 'concluido'
            AND strftime('%Y-%m', data_hora) = strftime('%Y-%m', 'now')
        ''')
        faturamento_mensal = cursor.fetchone()[0]
        
        # Faturamento da semana atual
        cursor.execute('''
            SELECT COALESCE(SUM(valor), 0)
            FROM agendamentos
            WHERE status = 'concluido'
            AND date(data_hora) >= date('now', 'weekday 0', '-6 days')
        ''')
        faturamento_semanal = cursor.fetchone()[0]
        
        # Faturamento do dia atual
        cursor.execute('''
            SELECT COALESCE(SUM(valor), 0)
            FROM agendamentos
            WHERE status = 'concluido'
            AND date(data_hora) = date('now')
        ''')
        faturamento_diario = cursor.fetchone()[0]
        
        # Contadores de agendamentos
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN status = 'pendente' THEN 1 END) as pendentes,
                COUNT(CASE WHEN status = 'confirmado' THEN 1 END) as confirmados,
                COUNT(CASE WHEN status = 'concluido' THEN 1 END) as concluidos,
                COUNT(CASE WHEN status = 'aguardando_confirmacao' THEN 1 END) as aguardando,
                COUNT(CASE WHEN status = 'cancelado' THEN 1 END) as cancelados
            FROM agendamentos
        ''')
        contadores = cursor.fetchone()
        
        # Faturamento por funcionário no mês com cálculo de porcentagem
        cursor.execute('''
            SELECT uf.nome, COUNT(a.id) as total_cortes, 
                   COALESCE(SUM(a.valor), 0) as total_faturado,
                   f.valor_corte, f.tipo_pagamento,
                   CASE 
                       WHEN f.tipo_pagamento = 'porcentagem' THEN 
                           COALESCE(SUM(a.valor * f.valor_corte / 100), 0)
                       ELSE 
                           COUNT(a.id) * f.valor_corte
                   END as valor_funcionario
            FROM agendamentos a
            JOIN funcionarios f ON a.funcionario_id = f.id
            JOIN usuarios uf ON f.usuario_id = uf.id
            WHERE a.status = 'concluido'
            AND strftime('%Y-%m', a.data_hora) = strftime('%Y-%m', 'now')
            GROUP BY f.id, uf.nome, f.valor_corte, f.tipo_pagamento
            ORDER BY total_cortes DESC
        ''')
        cortes_por_funcionario = cursor.fetchall()
        
        # Total de clientes
        cursor.execute('''
            SELECT COUNT(*) FROM usuarios WHERE tipo = 'cliente'
        ''')
        total_clientes = cursor.fetchone()[0]
        
        return {
            'faturamento_mensal': faturamento_mensal,
            'faturamento_semanal': faturamento_semanal,
            'faturamento_diario': faturamento_diario,
            'pendentes': contadores[0],
            'confirmados': contadores[1],
            'concluidos': contadores[2],
            'aguardando': contadores[3],
            'cancelados': contadores[4],
            'cortes_por_funcionario': cortes_por_funcionario,
            'total_clientes': total_clientes
        }

def obter_agenda_funcionario_por_data(funcionario_id, data_inicio, data_fim):
    """Obtém agenda do funcionário filtrada por período"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, u.nome as cliente, u.telefone, u.whatsapp, s.nome as servico,
                   strftime('%d/%m/%Y às %H:%M', a.data_hora) as data_hora_formatada, 
                   a.status, a.valor, date(a.data_hora) as data_agendamento,
                   strftime('%H:%M', a.data_hora) as horario
            FROM agendamentos a
            JOIN usuarios u ON a.cliente_id = u.id
            JOIN servicos s ON a.servico_id = s.id
            WHERE a.funcionario_id = ? 
            AND date(a.data_hora) BETWEEN ? AND ?
            ORDER BY a.data_hora ASC
        ''', (funcionario_id, data_inicio, data_fim))
        return cursor.fetchall()

def obter_faturamento_funcionario_periodo(funcionario_id, data_inicio, data_fim):
    """Obtém faturamento do funcionário em um período específico"""
    with obter_conexao() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(a.id) as total_cortes,
                   COALESCE(SUM(a.valor), 0) as total_faturado,
                   f.valor_corte, f.tipo_pagamento,
                   CASE 
                       WHEN f.tipo_pagamento = 'porcentagem' THEN 
                           COALESCE(SUM(a.valor * f.valor_corte / 100), 0)
                       ELSE 
                           COUNT(a.id) * f.valor_corte
                   END as valor_funcionario
            FROM agendamentos a
            JOIN funcionarios f ON a.funcionario_id = f.id
            WHERE a.funcionario_id = ? 
            AND a.status = 'concluido'
            AND date(a.data_hora) BETWEEN ? AND ?
            GROUP BY f.id, f.valor_corte, f.tipo_pagamento
        ''', (funcionario_id, data_inicio, data_fim))
        return cursor.fetchone()