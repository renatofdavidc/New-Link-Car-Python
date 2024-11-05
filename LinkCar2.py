#Imports das funcionalidades que serão utilizadas
import requests
import oracledb
import time


#Conexão com o banco de dados
def conectar_banco():
    try:
        with open('credenciais.txt', 'r') as arquivo:
            credenciais = [linha.strip() for linha in arquivo.readlines()]

        if len(credenciais) != 3:
            print('O arquivo de credencial deve ter somente 3 linhas!')

        user, password, dsn = credenciais

        conn = oracledb.connect(user=user, password=password, dsn=dsn)
        return conn
    except FileNotFoundError:
        print("Arquivo de credenciais não encontrado.")
        return None
    except ValueError as e:
        print(f"Erro no formato do arquivo de credenciais: {e}")
        return None
    except oracledb.DatabaseError as e:
        print(f'Erro ao conectar ao banco de dados: {e}')
        return None

#Receber o CEP do usuário
def obter_cep():
    cep = input('CEP: (ex. 01.310-100): ')
    cep = cep.replace('.', '').replace('-', '')
    return cep

#Validar formato do CEP
def validar_cep(cep):
    return len(cep) == 8

#Consultar os dados da API
def consultar_api_viacep(cep):
    url = f'https://viacep.com.br/ws/{cep}/json/'
    requisicao = requests.get(url)
    if requisicao.status_code == 200:
        return requisicao.json()
    else:
        print('Erro ao requerir o CEP!')
        return None

#Pegar os dados consultados da API e guardar em um dicionário
def extrair_dados(resposta):
    if resposta:
        return {
            'cep': resposta.get('cep').replace('-', ''),
            'uf': resposta.get('uf'),
            'cidade': resposta.get('localidade'),
            'rua': resposta.get('logradouro'),
            'bairro': resposta.get('bairro')
        }
    return None

#Variável global para armazenar o usuário atual logado, definido como none (nenhum usuário). Será alterada quando for feito login para algum usuário
usuario_logado = None

#Imprimir o menu principal
def menu():
    impressao_menu = '''
============== LINK CAR ==============
[1] - Criar conta
[2] - Login
[3] - Visualizar/Gerenciar contas
[4] - Registrar carro
[5] - Visualizar/Gerenciar carros
[6] - Registrar problema no carro
[7] - Integrantes
[8] - Sair
=======================================
'''
    print(impressao_menu)

#Ler e validar se a opção escolhida é válida
def ler_opcao(mensagem):
    while True:
        try:
            opcao = int(input(mensagem))
            return opcao
        except ValueError:
            print('Por favor, apenas utilize números!')
            input('Pressione Enter para tentar novamente...')

#Função para criar uma conta nova
def criar_conta(conn):
    email = input('Digite o email: ')
    
    #Verificar se o email já existe
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM usuarios WHERE email = :email", email=email)
        if cur.fetchone():
            print('Já existe um usuário com este email cadastrado!')
            return

    senha = input('Digite a senha: ')
    nome = input('Digite o seu nome completo: ')
    
    cep = obter_cep()
    if validar_cep(cep):
        resposta = consultar_api_viacep(cep)
        dados = extrair_dados(resposta)
        if dados:
            dados['nome'] = nome
            dados['email'] = email
            dados['senha'] = senha
            
            #Try para tratamento de erro
            try:
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO usuarios (nome, email, senha, cep, uf, cidade, rua, bairro)
                        VALUES (:nome, :email, :senha, :cep, :uf, :cidade, :rua, :bairro)
                    """
                    cur.execute(sql, dados)
                    conn.commit()
                    print('Conta criada com sucesso!')
            except oracledb.DatabaseError as e:
                print(f'Erro ao inserir dados no banco de dados: {e}')
        else:
            print('Erro ao obter dados do CEP.')
    else:
        print('CEP inválido!')
    
    input('Pressione Enter para voltar ao menu principal...')

#Função para listar contas registradas
def listar_contas(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nome, email, cep, uf, cidade, rua, bairro FROM usuarios")
            contas = cur.fetchall()
            
            for conta in contas:
                print('======================================================')
                print(f'ID: {conta[0]}')
                print(f"Nome: {conta[1]}")
                print(f"Email: {conta[2]}")
                print(f"CEP: {conta[3]}")
                print(f"UF: {conta[4]}")
                print(f"Cidade: {conta[5]}")
                print(f"Rua: {conta[6]}")
                print(f"Bairro: {conta[7]}")
                
                #Buscar e imprimir veículos associados a esta conta
                cur.execute("SELECT marca, modelo, placa FROM veiculos WHERE id_usuario = :id", id=conta[0])
                veiculos = cur.fetchall()
                
                if veiculos:
                    print("Veículos registrados:")
                    for veiculo in veiculos:
                        print(f"- {veiculo[0]} {veiculo[1]}, placa: {veiculo[2]}")
                
                print('======================================================')
    except oracledb.DatabaseError as e:
        print(f'Erro ao listar contas: {e}')
    
    #Tempo para ler a mensagem
    time.sleep(5)

#Função de login
def login(conn):
    global usuario_logado
    if usuario_logado:
        print('======================= LOGIN =======================')
        print(f'Você está logado como {usuario_logado["nome"]}')
        print('[1] - Entrar em outra conta')
        print('[2] - Sair da conta atual')
        print('[3] - Voltar ao menu principal')
        print('=====================================================')
        opcao = ler_opcao('Escolha uma opção: ')
        
        if opcao == 1:
            usuario_logado = None #Definido como none, para alterar a conta
            login(conn)
        elif opcao == 2:
            usuario_logado = None
            print('Você saiu da conta.')
        elif opcao == 3:
            return
    else:
        email_inserido = input('Digite o email: ')
        senha_inserida = input('Digite a senha: ')
        
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, nome, email FROM usuarios WHERE email = :email AND senha = :senha", 
                            email=email_inserido, senha=senha_inserida)
                conta = cur.fetchone()
                
                if conta:
                    usuario_logado = {'id': conta[0], 'nome': conta[1], 'email': conta[2]}
                    print(f'Login realizado com sucesso! Bem-vindo, {usuario_logado["nome"]}.')
                else:
                    print('Email ou senha incorretos!')
        except oracledb.DatabaseError as e:
            print(f'Erro ao realizar login: {e}')
        
        input('Pressione Enter para voltar ao menu principal...')

#Função para apagar contas
def apagar_conta(conn):
    listar_contas(conn)
    
    id_conta = ler_opcao('Digite o ID da conta a ser deletada: ')

    try:
        with conn.cursor() as cur:
            #Deletar os veículos associados à conta
            cur.execute("DELETE FROM veiculos WHERE id_usuario = :id", id=id_conta)
            
            # Deletar a conta
            cur.execute("DELETE FROM usuarios WHERE id = :id", id=id_conta)
            
            if cur.rowcount > 0:
                conn.commit()
                print(f'Conta ID {id_conta} removida com sucesso!')
            else:
                print(f'Conta ID {id_conta} não encontrada!')
    except oracledb.DatabaseError as e:
        print(f'Erro ao apagar conta: {e}')

    input('Pressione Enter para voltar ao menu principal...')

#Função para alterar informações das contas
def alterar_informacoes(conn, usuario_logado):
    print('[1] - Nome')
    print('[2] - Endereço')
    print('[3] - Email')
    print('[4] - Sair')
    opcao = ler_opcao('Escolha qual informação será alterada: ')
    
    if opcao == 1:
        novo_nome = input('Digite o novo nome: ')
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE usuarios SET nome = :nome WHERE id = :id", 
                            nome=novo_nome, id=usuario_logado['id'])
                conn.commit()
                usuario_logado['nome'] = novo_nome
                print(f'Nome alterado com sucesso para {novo_nome}')
        except oracledb.DatabaseError as e:
            print(f'Erro ao alterar nome: {e}')
    elif opcao == 2:
        cep = obter_cep()
        if validar_cep(cep):
            resposta = consultar_api_viacep(cep)
            dados = extrair_dados(resposta)
            if dados:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE usuarios 
                            SET cep = :cep, uf = :uf, cidade = :cidade, rua = :rua, bairro = :bairro 
                            WHERE id = :id
                        """, cep=dados['cep'], uf=dados['uf'], cidade=dados['cidade'], 
                             rua=dados['rua'], bairro=dados['bairro'], id=usuario_logado['id'])
                        conn.commit()
                        print('Endereço atualizado com sucesso!')
                except oracledb.DatabaseError as e:
                    print(f'Erro ao atualizar endereço: {e}')
            else:
                print('Erro ao obter dados do CEP.')
        else:
            print('CEP inválido!')
    elif opcao == 3:
        novo_email = input('Digite o novo email: ')
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE usuarios SET email = :email WHERE id = :id", 
                            email=novo_email, id=usuario_logado['id'])
                conn.commit()
                usuario_logado['email'] = novo_email
                print(f'Email alterado com sucesso para {novo_email}')
        except oracledb.DatabaseError as e:
            print(f'Erro ao alterar email: {e}')
    
    input('Pressione Enter para retornar...')

#Submenu do gerenciamento de contas
def sub_informacoes_conta(conn):
    print('===================================== ALTERAR INFORMAÇÕES DA CONTA =====================================')
    print(f'Você está logado como {usuario_logado["nome"]}')
    print('Por questões de segurança, para alterar as informações de uma conta, você precisa estar logado nela.')
    print('[1] - Mudar de conta (Ir para a tela de login)')
    print('[2] - Alterar informações da conta')
    print('[3] - Voltar ao menu principal')
    print('========================================================================================================')
    opcao = ler_opcao('Escolha uma opção: ')
    match opcao:
        case 1:
            login(conn)
        case 2:
            alterar_informacoes(conn, usuario_logado)
        case 3:
            return
        case _:
            print('Opção inválida!')
            input('Pressione Enter para retornar ao menu principal...')

#Submenu de gerenciamento de contas
def gerenciar_contas(conn):
    print('======== GERENCIAMENTO DE CONTAS ========')
    print('[1] - Visualizar contas')
    print('[2] - Apagar uma conta')
    print('[3] - Alterar informações de uma conta')
    print('[4] - Voltar ao menu principal')
    print('==========================================')
    opcao = ler_opcao('Escolha uma opção: ')
    match opcao:
        case 1:
            listar_contas(conn)
        case 2:
            apagar_conta(conn)
        case 3:
            sub_informacoes_conta(conn)
        case 4:
            return
        case _:
            print('Opção inválida!')
            input('Pressione Enter para retornar ao menu principal...')

#Registrar um veículo e associá-lo ao usuário logado
def registrar_veiculo(conn):
    global usuario_logado
    print('======================== REGISTRO DE CARRO ========================')
    print(f'Você está logado como {usuario_logado["nome"]}. O carro registrado estará ligado a este usuário.')
    
    chassi = input('Por favor, informe o número do chassi do carro: ')
    
    if len(chassi) == 17:
        marca = input('Por favor, informe a marca do carro: ')
        modelo = input('Por favor, informe o modelo do carro: ')
        cor = input('Por favor, informe a cor do carro: ')
        placa = input('Por favor, informe a placa do carro (ABC1D23) ou (ABC-1234): ')
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO veiculos (id_usuario, chassi, marca, modelo, cor, placa)
                    VALUES (:id_usuario, :chassi, :marca, :modelo, :cor, :placa)
                """, id_usuario=usuario_logado['id'], chassi=chassi, marca=marca, 
                     modelo=modelo, cor=cor, placa=placa)
                conn.commit()
                print(f"Veículo {marca} {modelo} registrado com sucesso para {usuario_logado['nome']}!")
        except oracledb.DatabaseError as e:
            print(f'Erro ao registrar veículo: {e}')
    else:
        print('Número do chassi inválido! Verifique a quantidade de caracteres...')
    
    input('Pressione Enter para retornar ao menu principal...')

#Função para visualizar os veículos cadastrados
def visualizar_veiculos(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, marca, modelo, cor, placa, chassi 
                FROM veiculos 
                WHERE id_usuario = :id_usuario
            """, id_usuario=usuario_logado['id'])
            veiculos = cur.fetchall()
            
            if veiculos:
                #Imprimir as informações do veículo
                print(f'Veículos cadastrados por {usuario_logado["nome"]}:')
                for veiculo in veiculos:
                    print('=============================================')
                    print(f"ID: {veiculo[0]}")
                    print(f"Marca: {veiculo[1]}")
                    print(f"Modelo: {veiculo[2]}")
                    print(f"Cor: {veiculo[3]}")
                    print(f"Placa: {veiculo[4]}")
                    print(f"Chassi: {veiculo[5]}")
                    print('=============================================')
            else:
                print('Você não tem veículos cadastrados.')
    except oracledb.DatabaseError as e:
        print(f'Erro ao visualizar veículos: {e}')

    input('Pressione Enter para voltar ao menu...')

#Função para apagar um veículo
def apagar_veiculo(conn):
    visualizar_veiculos(conn)
    id_veiculo = ler_opcao('Informe o ID do veículo que deseja remover: ')
    
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM veiculos WHERE id = :id AND id_usuario = :id_usuario", 
                        id=id_veiculo, id_usuario=usuario_logado['id'])
            if cur.rowcount > 0:
                conn.commit()
                print(f'Veículo ID {id_veiculo} removido com sucesso!')
            else:
                print('Veículo não encontrado ou não pertence a este usuário.')
    except oracledb.DatabaseError as e:
        print(f'Erro ao apagar veículo: {e}')
    
    input('Pressione Enter para voltar ao menu...')

#Função para alterar as informações de um veículo
def alterar_informacoes_veiculo(conn):
    visualizar_veiculos(conn)
    id_veiculo = ler_opcao('Informe o ID do veículo que deseja alterar: ')
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT marca, modelo, cor, placa 
                FROM veiculos 
                WHERE id = :id AND id_usuario = :id_usuario
            """, id=id_veiculo, id_usuario=usuario_logado['id'])
            veiculo = cur.fetchone()
            
            if veiculo:
                print(f'Alterando informações do veículo {veiculo[0]} {veiculo[1]}:')
                nova_marca = input(f'Informe a nova marca (atual: {veiculo[0]}): ') 
                novo_modelo = input(f'Informe o novo modelo (atual: {veiculo[1]}): ') 
                nova_cor = input(f'Informe a nova cor (atual: {veiculo[2]}): ') 
                nova_placa = input(f'Informe a nova placa (atual: {veiculo[3]}): ') 
                
                cur.execute("""
                    UPDATE veiculos 
                    SET marca = :marca, modelo = :modelo, cor = :cor, placa = :placa 
                    WHERE id = :id AND id_usuario = :id_usuario
                """, marca=nova_marca, modelo=novo_modelo, cor=nova_cor, placa=nova_placa, 
                     id=id_veiculo, id_usuario=usuario_logado['id'])
                conn.commit()
                print('Informações alteradas com sucesso!')
            else:
                print('Veículo não encontrado ou não pertence a este usuário.')
    except oracledb.DatabaseError as e:
        print(f'Erro ao alterar informações do veículo: {e}')
    
    input('Pressione Enter para voltar ao menu...')

#Submenu de gerenciamento de veículos
def gerenciar_veiculos(conn):
    print('======== GERENCIAMENTO DE VEÍCULOS ========')
    print('[1] - Visualizar veículos')
    print('[2] - Apagar um veículo')
    print('[3] - Alterar informações de um veículo')
    print('[4] - Voltar ao menu principal')
    print('===========================================')
    opcao = ler_opcao('Escolha uma opção: ')
    match opcao:
        case 1:
            visualizar_veiculos(conn)
        case 2:
            apagar_veiculo(conn)
        case 3:
            alterar_informacoes_veiculo(conn)
        case 4:
            return
        case _:
            print('Opção inválida!')
            input('Pressione Enter para retornar ao menu...')

#Função para registrar um problema, em um veículo do usuário logado
def registrar_problema(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, marca, modelo, placa 
                FROM veiculos 
                WHERE id_usuario = :id_usuario
            """, id_usuario=usuario_logado['id'])
            veiculos = cur.fetchall()
            
            if not veiculos:
                print('Você não tem veículos cadastrados.')
                input('Pressione Enter para voltar ao menu...')
                return

            print(f"Veículos cadastrados por {usuario_logado['nome']}:")
            for i, veiculo in enumerate(veiculos, 1):
                print(f"[{i}] {veiculo[1]} {veiculo[2]}, placa: {veiculo[3]}")

            opcao = ler_opcao('Escolha o número do veículo para registrar o problema: ')

            if 1 <= opcao <= len(veiculos):
                veiculo_escolhido = veiculos[opcao - 1]
                problema = input('Por favor, informe o problema encontrado no veículo: ')

                cur.execute("""
                    INSERT INTO problemas (id_veiculo, descricao)
                    VALUES (:id_veiculo, :descricao)
                """, id_veiculo=veiculo_escolhido[0], descricao=problema)
                conn.commit()

                print(f"Problema de '{problema}' no carro {veiculo_escolhido[1]} {veiculo_escolhido[2]} "
                      f"de {usuario_logado['nome']} registrado, e será verificado para um diagnóstico.")
            else:
                print('Opção inválida!')
    except oracledb.DatabaseError as e:
        print(f'Erro ao registrar problema: {e}')

    input('Pressione Enter para voltar ao menu...')

#Lógica principal do programa
def main():
    conn = conectar_banco()
    if not conn:
        print("Não foi possível conectar ao banco de dados. O programa será encerrado.")
        return

    while True:
        menu()
        opcao = ler_opcao('Escolha uma opção: ')
        match opcao:
            case 1:
                criar_conta(conn)
            case 2:
                login(conn)
            case 3:
                if usuario_logado:
                    gerenciar_contas(conn)
                else:
                    print('Você não está logado!')
                    input('Pressione Enter para retornar...')
            case 4:
                if usuario_logado:
                    registrar_veiculo(conn)
                else:
                    print('Você não está logado!')
                    input('Pressione Enter para retornar...')
            case 5:
                if usuario_logado:
                    gerenciar_veiculos(conn)
                else:
                    print('Você não está logado!')
                    input('Pressione Enter para retornar...')
            case 6:
                if usuario_logado:
                    registrar_problema(conn)
                else:
                    print('Você não está logado!')
                    input('Pressione Enter para retornar...')
            case 7:
                print('================================== INTEGRANTES ==================================')
                print('Renato de Freitas David Campiteli - RM555627 - https://github.com/renatofdavidc')
                print('Pedro Lucas de Oliveira Bezerra - RM558439 - https://github.com/PedrinDev1447')
                print('Gabriel Santos Jablonski - RM555425 - https://github.com/Jablonski17')
                print('=================================================================================')
                input('Pressione Enter para voltar ao menu principal...')
            case 8:
                print('Saindo...')
                break
            case _:
                print('Opção inválida!')

    conn.close()

#Executa o programa
main()