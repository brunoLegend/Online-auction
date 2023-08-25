##
## =============================================
## ============== Bases de Dados ===============


 
from flask import Flask, jsonify, request
import logging, psycopg2, time, random, os

app = Flask(__name__) 


@app.route('/') 
def hello(): 
    return """

    Hello World!  <br/>
    <br/>
    Check the sources for instructions on how to use the endpoints!<br/>
    <br/>
    BD 2021 Team<br/>
    <br/>
    """

## Get all the current auctions (leiloes)

@app.route("/dbproj/leiloes/", methods=['GET'], strict_slashes=True)
def get_all_leiloes_ativos():
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT utilizadorid, authToken FROM utilizador WHERE authToken = %s AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    #auctions that still didn't finished
    cur.execute("SELECT leilaoid, descricao FROM leilao WHERE NOW() + INTERVAL '1' HOUR <= fim AND cancelado = false")
    rows = cur.fetchall()

    payload = []
    logger.debug("---- leiloes a decorrer ----")
    for row in rows:
        logger.debug(row)
        content = {'leilaoId': int(row[0]), 'descricao': row[1]}
        payload.append(content) # appending to the payload to be returned

    conn.close()
    return jsonify(payload)


## Get auctions with  <leilaoid>

@app.route("/dbproj/leilao/<leilaoid>", methods=['GET'])
def get_leilao_by_id(leilaoid):
    headers = request.headers

    logger.info("###              DEMO: GET /leilao/<leilaoid>              ###");   

    logger.debug(f'leilaoid: {leilaoid}')
    logger.debug(headers["authToken"])

    conn = db_connection()
    cur = conn.cursor()


    ##Check if Token is valid
    cur.execute("SELECT utilizadorid, authToken FROM utilizador where authToken = %s AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    #gET auction
    cur.execute("SELECT leilaoid, titulo, descricao, precomin, artigo_codigo, utilizadorid FROM leilao WHERE leilaoid = %s", (leilaoid,))
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close ()
        return jsonify({'erro': 'eleicao nao existe'})

    row = rows[0]

    #GET auction messages
    cur.execute("SELECT mensagem, data, utilizadorid, leilaoid FROM mural WHERE leilaoid = %s", (leilaoid,))
    rows2 = cur.fetchall()

    payload_mensagens = []
    for row2 in rows2:
        content = {'mensagem': row2[0], 'data': row2[1], 'utilizadorid': row2[2]}
        payload_mensagens.append(content)


    #Get auction bids
    cur.execute("SELECT valor, utilizadorid, data, leilaoid FROM licitacao WHERE leilaoid = %s", (leilaoid,))
    rows2 = cur.fetchall()

    payload_licitacoes = []
    for row2 in rows2:
        content = {'valor': row2[0], 'utilizadorid': row2[1], 'data': row2[2]}
        payload_licitacoes.append(content)    

    
    content = {'leilaoId': row[0], 'titulo': row[1], 'descricao': row[2], 'precomin': row[3], 'artigo_codigo': row[4], 'utilizadorid': row[5], 'mural': payload_mensagens, 'licitações': payload_licitacoes}

    conn.close ()
    return jsonify(content)

## Get auction with <artigoid || descrição_artigo>

@app.route("/dbproj/leiloes/<keyword>", methods=['GET'])
def get_leilao(keyword):
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    #Check if token is valid
    cur.execute("SELECT utilizadorid, authToken FROM utilizador WHERE authToken = %s AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    #Search by id and description
    if(keyword.isdecimal()):
        statement = """
                    SELECT leilaoid, titulo, descricao, precomin, artigo_codigo, utilizadorid 
                    FROM leilao 
                    WHERE artigo_codigo IN (SELECT codigo
                                        FROM artigo AS A 
                                        WHERE A.codigo = %s OR A.descricao LiKE %s)
                    """
        values = (int(keyword), like(keyword, 2))        
    
    #Search by description
    else:
        statement = """
                    SELECT leilaoid, titulo, descricao, precomin, artigo_codigo, utilizadorid 
                    FROM leilao 
                    WHERE artigo_codigo IN (SELECT codigo 
                                        FROM artigo AS A 
                                        WHERE A.descricao LiKE %s) 
                    """
        values = (like(keyword, 2),)         

    try:
        logger.debug(statement)
        logger.debug(values)
        cur.execute(statement, values)
        rows = cur.fetchall()
        
        payload = []
        for row in rows:
            content = {'leilaoId': int(row[0]), 'titulo': row[1], 'descricao': row[2], 'precomin': int(row[3]), 'artigo_codigo': int(row[4]), 'utilizadorid': int(row[5])}
            payload.append(content)

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        payload =  {'erro': 'Nao encontrado'}
    finally:
        if conn is not None:
            conn.close()

    return jsonify(payload)


## Get Older versions of the auction <leilaoid>

@app.route("/dbproj/versoesant/<leilaoid>", methods=['GET'])
def get_versoesant_leilao_by_id(leilaoid):
    headers = request.headers
    
    conn = db_connection()
    cur = conn.cursor()

    ##Check if the token is valid
    cur.execute("SELECT utilizadorid, authToken FROM utilizador where authToken = %s AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    #cHECK if the auction exists
    cur.execute("SELECT leilaoid FROM leilao WHERE leilaoid = %s", (leilaoid,))
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close ()
        return jsonify({'erro': 'leilao nao existe'})


    #Get previous versions of the auction
    cur.execute("SELECT titulo, descricao, data FROM versoesant WHERE leilaoid = %s", (leilaoid,))
    rows = cur.fetchall()

    payload = []
    for row in rows:
        content = {'titulo': row[0], 'descricao': row[1], 'data': row[2]}
        payload.append(content)

    
    
    conn.close ()
    return jsonify(payload)


## register new auction

@app.route("/dbproj/leilao/", methods=['POST'])
def add_leilao():
    payload = request.get_json()
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    ##Get User ID
    cur.execute("SELECT utilizadorid, authToken FROM utilizador WHERE authToken = %s AND isadmin = false AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    utilizadorid = rows[0][0]

    ##cREATE auction
    statement = """
                  INSERT INTO leilao (inicio, fim, titulo, descricao, cancelado, precomin, licitacaomaior, artigo_codigo, utilizadorid) 
                          VALUES (NOW() + INTERVAL '1' HOUR, %s, %s, %s, false, %s, 0, %s, %s)
                  RETURNING leilaoid        """

    values = (timeStamp(payload["diaFim"], payload["horaFim"]), payload["titulo"], payload["descricao"], payload["precoMinimo"], payload["artigoId"], utilizadorid)

    try:
        cur.execute(statement, values)
        
        rows = cur.fetchall()
        leilaoid = rows[0][0]
        
        result = {"leilaoId": leilaoid} 

        cur.execute("commit")

    #except ("Artigo nao pode ser adicionado", psycopg2.DatabaseError) as error:
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result =  {'erro': "nao foi possivel criar o leilão"}
    finally:
        if conn is not None:
            conn.close()
    
    return jsonify(result)

## Edit auction

@app.route("/dbproj/leilao/<leilaoid>", methods=['PUT'])
def editar_leilao(leilaoid):
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    ##Get User ID
    cur.execute("SELECT utilizadorid, authToken FROM utilizador WHERE authToken = %s AND isadmin = false AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    utilizadorid = rows[0][0]

    #check if auction exists and if the user can edit it
    cur.execute("SELECT leilaoid, utilizadorid FROM leilao where leilaoid = %s AND utilizadorid = %s", (leilaoid, utilizadorid) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'Não pode alterar este leilão'})


    if "titulo" in headers:
        #title and description
        if "descricao" in headers:
            statement = """
                        UPDATE leilao
                        SET titulo = %s, descricao = %s
                        WHERE leilaoid = %s AND utilizadorid = %s
                        RETURNING leilaoid, titulo, descricao, precomin, artigo_codigo, utilizadorid, cancelado, fim, licitacaomaior, inicio
                        """

            values = (headers["titulo"], headers["descricao"], utilizadorid, leilaoid)

        #just title
        else:
            statement = """
                        UPDATE leilao
                        SET titulo = %s
                        WHERE leilaoid = %s AND utilizadorid = %s
                        RETURNING leilaoid, titulo, descricao, precomin, artigo_codigo, utilizadorid, cancelado, fim, licitacaomaior, inicio
                        """

            values = (headers["titulo"], utilizadorid, leilaoid)

    #Just description
    else:
        statement = """
                    UPDATE leilao
                    SET descricao = %s
                    WHERE leilaoid = %s AND utilizadorid = %s
                    RETURNING leilaoid, titulo, descricao, precomin, artigo_codigo, utilizadorid, cancelado, fim, licitacaomaior, inicio
                    """

        values = (headers["descricao"], utilizadorid, leilaoid)


    try:
        cur.execute(statement, values)
        rows = cur.fetchall()
        row = rows[0]

        result = {'leilaoId': int(row[0]), 'titulo': row[1], 'descricao': row[2], 'precomin': int(row[3]),'artigo_codigo': int(row[4]), 'utilizadorid': int(row[5]), 'cancelado': row[6], 'fim':row[7], 'maior licitacao': row[8], 'inicio': row[9]}
       
        cur.execute("commit")

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result =  {'erro': 'codigoErro'}
    finally:
        if conn is not None:
            conn.close()
    
    return jsonify(result)


## Register new user

@app.route("/dbproj/user/", methods=['POST'])
def add_user():
    payload = request.get_json()
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT utilizadorid, authToken FROM utilizador where authToken = %s AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    statement = """
                INSERT INTO utilizador (username, password, email, ban, isadmin)
                    VALUES (%s,   %s ,   %s , false, false)
                RETURNING utilizadorid    
                    """

    values = (payload["username"], payload["password"], payload["email"])

    try:
        cur.execute(statement, values)
        
        #GET userID
        logger.debug("sera que deu bem?");
        rows = cur.fetchall()
        logger.debug("deu!");
        logger.debug(rows);
        result = {'userId': rows[0][0]} 
        cur.execute("commit")
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result =  {'erro': 'codigoErro'}
    finally:
        if conn is not None:
            conn.close()
    
    return jsonify(result)

## Autentication

@app.route("/dbproj/user/", methods=['PUT'])
def do_login():
    logger.info("###              DEMO: PUT /user           ###");   

    payload = request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT utilizadorid, username, password FROM utilizador where username = %s and password = %s AND ban = false", (payload["username"], payload["password"],))
    rows = cur.fetchall()

    #erro -> nao encontrado ou houve algum problema
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'AuthError1'})

    row = rows[0]

    #definir authToken
    authToken = row[0] #provisorio
    #atualizar utilizador com o authtoken
    statement = """
                UPDATE utilizador
                SET authToken = %s,
                    data_expiracao = NOW() + INTERVAL '2' HOUR
                WHERE utilizadorid = %s """

    values = (authToken, row[0])

    try:
        cur.execute(statement, values)
        cur.execute("commit")
        result = {'authToken': authToken} 
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result = {'erro': 'AuthError2'}
    finally:
        if conn is not None:
            conn.close()
    
    return jsonify(result)

##Listar todos os leilões em que o user tenha atividade

@app.route("/dbproj/atividade/",methods=['GET'],strict_slashes=True)
def get_all_leiloes_ativi():
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()


    ##Verificar se o Token é valido
    cur.execute("SELECT utilizadorid, authToken FROM utilizador where authToken = %s AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    utilizadorid = rows[0][0]

    cur.execute("SELECT titulo, descricao FROM leilao where utilizadorid = %s AND cancelado = false", (utilizadorid,))
    rows = cur.fetchall()

    payload = []
    for row in rows:
        logger.debug(row)
        content = {'titulo': row[0], 'descricao': row[1]}
        payload.append(content) # appending to the payload to be returned

    payload_licitar = []


    cur.execute("SELECT leilaoid,data FROM licitacao WHERE utilizadorid = %s",(utilizadorid,))
    rows=cur.fetchall()
    for row in rows:
        logger.info(row)
        content={'leilaoid ':row[0],'data':row[1]}
        payload_licitar.append(content)


    conn.close()
    return jsonify({'criados pelo user': payload, 'licitou': payload_licitar}) 


## Escrever mensagem num leilão

@app.route("/dbproj/mural/<leilaoid>", methods=['POST'], strict_slashes=True)
def add_mensagem_mural(leilaoid):
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    ##obter o ID do utilizador
    cur.execute("SELECT utilizadorid, authToken FROM utilizador WHERE authToken = %s AND isadmin = false AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    utilizadorid = rows[0][0]

    #INSERT lista de murais dos leilões
    statement = """
                INSERT INTO mural (mensagem, data, leilaoid, utilizadorid)
                    VALUES (%s,   NOW() + INTERVAL '1' HOUR ,   %s , %s)
                    """
    values = (headers["mensagem"], int(leilaoid), utilizadorid)

    try:
        cur.execute(statement, values)
        cur.execute("commit")
        result = {'Estado': 'mensagem submetida'} 
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result = {'Estado': 'mensagem não submetida'}
    finally:
        if conn is not None:
            conn.close()

    return jsonify(result)         

## ler mensagens de um leilao

@app.route("/dbproj/notificacao/novas/", methods=['GET'], strict_slashes=True)
def get_mensagem_utilizador_novas():
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    ##obter o ID do utilizador
    cur.execute("SELECT utilizadorid, authToken FROM utilizador WHERE authToken = %s AND isadmin = false AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    utilizadorid = rows[0][0]

    payload = []
    cur.execute("SELECT mensagem, data FROM notificacao WHERE utilizadorid = %s AND recebida = false", (utilizadorid,))
    rows = cur.fetchall()
    for row in rows:
        logger.info(row)
        content = {'mensagem ': row[0], 'data': row[1]}
        payload.append(content)

    try:

        statement = """
                    UPDATE notificacao
                    SET recebida = true
                    WHERE utilizadorid = %s
                    """

        values = (utilizadorid,)

        cur.execute(statement, values)
        cur.execute("commit")

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result =  {'erro': 'codigoErro'}
    finally:
        if conn is not None:
            conn.close()

    return jsonify(payload)             


## ler notificacoes lidas

@app.route("/dbproj/notificacao/lidas/", methods=['GET'], strict_slashes=True)
def get_mensagem_utilizador_lidas():
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    ##obter o ID do utilizador
    cur.execute("SELECT utilizadorid, authToken FROM utilizador WHERE authToken = %s AND isadmin = false AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    utilizadorid = rows[0][0]

    payload = []
    cur.execute("SELECT mensagem, data FROM notificacao WHERE utilizadorid = %s AND recebida = true", (utilizadorid,))
    rows = cur.fetchall()
    for row in rows:
        logger.info(row)
        content = {'mensagem ': row[0], 'data': row[1]}
        payload.append(content)

    conn.close()

    return jsonify(payload)             


## Efetuar nova licitacao no leilao

@app.route("/dbproj/licitar/<leilaoid>/<licitacao>", methods=['GET'])
def licitar_leilao(leilaoid, licitacao):

    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    ##obter o ID do utilizador
    cur.execute("SELECT utilizadorid, authToken FROM utilizador WHERE authToken = %s AND isadmin = false AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    utilizadorid = rows[0][0]    

    #verificar se o leilao pretendido existe e ainda nao terminou
    cur.execute("SELECT leilaoid, precomin, licitacaomaior FROM leilao where NOW() + INTERVAL '1' HOUR <= fim AND leilaoid = %s AND utilizadorid != %s AND cancelado = false", (leilaoid, utilizadorid))
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'leilao nao existe ou é o criador do leilão'})
    row = rows[0]

    #fazer nova licitacao se for maior que licitacaomaior e precomin
    if float(licitacao) >= float(row[1]) and float(licitacao) > float(row[2]):
        statement = """
            INSERT INTO licitacao (leilaoid, valor, valido, data, utilizadorid)
            VALUES (%s,   %s, true, NOW() + INTERVAL '1' HOUR, %s);
                UPDATE leilao
                        SET licitacaomaior = %s
                        WHERE leilaoid = %s  
            """

        values = (row[0], licitacao, utilizadorid, licitacao, leilaoid)
    else:
        conn.close()
        return jsonify({'erro': 'licitacao invalida'})
        
    try:
        cur.execute(statement, values)
        
        result = {"Sucesso": "licitadao efectuada"} 

        cur.execute("commit")

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result =  {'erro': 'codigoErro'}
    finally:
        if conn is not None:
            conn.close()

     
    return jsonify(result)


## Registar novo leilão

@app.route("/dbproj/artigo/", methods=['POST'])
def add_artigo():
    payload = request.get_json()
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    ##obter o ID do utilizador
    cur.execute("SELECT utilizadorid, authToken FROM utilizador WHERE authToken = %s AND isadmin = false AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})

    utilizadorid = rows[0][0]

    ##criar artigo
    statement = """
                INSERT INTO artigo (codigo, nome, descricao, vendido) 
                    VALUES (%s, %s, %s, false)
                RETURNING codigo        
                """

    values = (payload["codigo"], payload["nome"], payload["descricao"])

    try:
        cur.execute(statement, values)
        
        rows = cur.fetchall()
        codigo = rows[0][0]
        
        result = {"codigo artigo": codigo} 

        cur.execute("commit")

    #except ("Artigo nao pode ser adicionado", psycopg2.DatabaseError) as error:
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result =  {'erro': "nao foi possivel adicionar o artigo"}
    finally:
        if conn is not None:
            conn.close()
    
    return jsonify(result)

##ADMIN

## Admin a banir utilizador permanentemente

@app.route("/dbproj/banir/", methods=['POST'])

def banir_user(): #recebe id do utilizador a ser banido
    
    headers = request.headers
    
    conn = db_connection()
    cur = conn.cursor()

    ##obter o ID do utilizador que vai banir outro
    cur.execute("SELECT utilizadorid, authToken, isadmin FROM utilizador where authToken = %s AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (headers["authToken"],) )
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'authToken invalido'})
    row = rows[0]

    ##verificar se utilizador e admin
    if row[2]:
        statement = """
                    UPDATE utilizador
                    SET ban = true
                    WHERE utilizadorid = %s and ban = false
                    RETURNING utilizadorid
                    """
        values = ((headers["utilizadorid"],))
    else:
        conn.close()
        return jsonify({'erro': 'nao é Admin'})

    try:
        cur.execute(statement, values)
        rows = cur.fetchall()
        if len(rows) < 1:
            result = {'erro': 'user ja banido'}
        else:
            result = {'sucesso': headers["utilizadorid"]}
         
        #result = {"Sucesso": "aaa"} 
        cur.execute("commit")

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        result =  {'erro': 'codigoErro'}
    finally:
        if conn is not None:
            conn.close()

    return jsonify(result)


##Cancelar leilão

@app.route("/dbproj/cancel/",methods=["POST"])
def cancel_leilao():
    #gets leilao_id
    headers = request.headers

    conn = db_connection()
    cur = conn.cursor()

    leilao_id = headers["leilaoId"]
    authToken = headers["authToken"]
    logger.info(leilao_id)

    cur.execute("SELECT isadmin FROM utilizador WHERE authToken = %s AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false", (authToken,))
    rows = cur.fetchall()
    if(len(rows) < 1):
        conn.close()
        return jsonify({'erro': 'Utilizador não existe'})
    if(rows[0][0] == False):
        conn.close()
        return jsonify({'erro': 'Utilizador não é um admin'})

    ##################################################################

    cur.execute("SELECT cancelado FROM leilao where leilaoId = %s", (leilao_id,))
    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'leilaoId nao existe'})
    
    logger.info(rows[0][0])
    if(rows[0][0] == True):
        conn.close()
        return jsonify({'erro': 'leilão já cancelado'})

    cur.execute("UPDATE leilao SET cancelado = true WHERE leilaoId = %s AND NOW() + INTERVAL '1' HOUR <= fim RETURNING cancelado",(leilao_id,))

    rows = cur.fetchall()
    if len(rows) < 1:
        conn.close()
        return jsonify({'erro': 'não pode cancelar este leilao'})

    content = {'leilaoId': leilao_id, 'estado': 'cancelado'}
    
    cur.execute("commit")

    return jsonify({'Sucesso': content})


## Estatísticas da atividade

@app.route("/dbproj/estatisticas/", methods=['GET'])
def get_stats():

    headers = request.headers
    authToken = headers["authToken"]

    conn = db_connection()
    cur = conn.cursor()

    ##### Verificar se o utilizador é um admin ##########################

    cur.execute("SELECT isadmin FROM utilizador WHERE authToken = %s AND data_expiracao >= NOW() + INTERVAL '1' HOUR AND ban = false",(authToken,))
    rows = cur.fetchall()
    if(len(rows)<1):
        conn.close()
        return jsonify({'erro': 'Utilizador não existe'})
    if(rows[0][0] == False):
        conn.close()
        return jsonify({'erro': 'Utilizador não é um admin'})

    #numero de leiloes nos ultimos 10 dias
    cur.execute("SELECT COUNT(leilaoid) FROM leilao WHERE fim >= NOW() + INTERVAL '1' HOUR - INTERVAL '10' DAY AND fim <= NOW() + INTERVAL '1' HOUR")

    row = cur.fetchall()
    num_leiloes = row[0][0]

    ##leiloes criados
    statement = """
            SELECT username, COUNT(username)
            FROM utilizador, leilao 
            WHERE utilizador.utilizadorid = leilao.utilizadorid AND leilao.cancelado = false 
            GROUP BY username 
            ORDER BY COUNT(username) DESC LIMIT 10
            """

    cur.execute(statement)
    rows = cur.fetchall()
    
    payload_leiloes_criados = []
    for row in rows:    
        content = {'nome': row[0], 'numero de leiloes': row[1]}
        payload_leiloes_criados.append(content) # appending to the payload to be returned

    ##leiloes ganhos
    statement = """
            SELECT username, COUNT(username)
            FROM utilizador, leilao, licitacao
            WHERE utilizador.utilizadorid = leilao.utilizadorid AND utilizador.utilizadorid = licitacao.utilizadorid
            AND leilao.fim <= NOW() + INTERVAL '1' HOUR AND leilao.cancelado = false AND leilao.licitacaomaior > 0
            AND leilao.licitacaomaior = licitacao.valor AND licitacao.valido = true
            GROUP BY username
            ORDER BY COUNT(username) DESC LIMIT 10
            """

    cur.execute(statement)
    rows = cur.fetchall()
    
    payload_leiloes_ganhos = []
    for row in rows:
        content = {'nome ': row[0], 'leiloes ganhos': row[1]}
        payload_leiloes_ganhos.append(content)
    
    conn.close()
    return jsonify({'top 10 users com mais leiloes criados': payload_leiloes_criados, 'top users 10 com mais leiloes ganhos ': payload_leiloes_ganhos,'Número total de leilões nos últimos 10 dias ': num_leiloes})      

##AUXILIARES

## Obter todos os leiloes 

@app.route("/dbproj/leiloesAll/", methods=['GET'], strict_slashes=True)
def get_all_leiloes():
    logger.info("###              DEMO: GET /leiloes              ###");

    conn = db_connection()
    cur = conn.cursor()

    #leiloes que ainda não terminaram
    cur.execute("SELECT leilaoid, titulo, descricao, precomin, artigo_codigo, utilizadorid, cancelado, fim, licitacaomaior, inicio FROM leilao")
    rows = cur.fetchall()

    payload = []
    for row in rows:
        logger.debug(row)
        content = {'leilaoId': int(row[0]), 'titulo': row[1], 'descricao': row[2], 'precomin': int(row[3]),'artigo_codigo': int(row[4]), 'utilizadorid': int(row[5]), 'cancelado': row[6], 'fim':row[7], 'maior licitacao': row[8], 'inicio': row[9]}
        payload.append(content)

    conn.close()
    return jsonify(payload)

## Obter todos os utilizadores

@app.route("/dbproj/user/", methods=['GET'], strict_slashes=True)
def get_all_utilizadores():
    logger.info("###              DEMO: GET /utilizadores              ###");   

    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT username, password FROM utilizador")
    rows = cur.fetchall()

    payload = []
    logger.debug("---- utilizadores  ----")
    for row in rows:
        logger.debug(row)
        content = {'username': row[0], 'password': row[1]}
        payload.append(content) # appending to the payload to be returned

    conn.close()
    return jsonify(payload)

## Obter todos os artigos

@app.route("/dbproj/artigos/", methods=['GET'], strict_slashes=True)
def get_all_artigos():
    logger.info("###              DEMO: GET /artigos              ###");   

    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT codigo, nome FROM artigo")
    rows = cur.fetchall()

    payload = []
    logger.debug("---- artigos  ----")
    for row in rows:
        logger.debug(row)
        content = {'codigo': row[0], 'nome': row[1]}
        payload.append(content) # appending to the payload to be returned

    conn.close()
    return jsonify(payload)    


## Obter utilizador com utilizadorid <utilizadorid>

@app.route("/dbproj/user/<utilizadorid>", methods=['GET'])
def get_utilizador(utilizadorid):
    logger.info("###              DEMO: GET /utilizadores/<utilizadorid>              ###");   

    logger.debug(f'utilizadorid: {utilizadorid}')

    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT utilizadorid, username FROM utilizador where utilizadorid = %s", (utilizadorid,) )
    rows = cur.fetchall()

    row = rows[0]

    logger.debug("---- selected utilizador  ----")
    logger.debug(row)
    content = {'utilizadorid': int(row[0]), 'username': row[1]}

    conn.close ()
    return jsonify(content)        

## GET todas as mensagens do mural

@app.route("/dbproj/mural", methods=['GET'], strict_slashes=True)
def get_all_mensagens_mural():
    logger.info("###              DEMO: GET /leiloes              ###");   

    payload = request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    #INSERT lista de murais dos leilões
    cur.execute("SELECT mensagem, data, leilaoid, utilizadorid FROM mural")
    rows = cur.fetchall()

    payload = []
    logger.debug("---- mural  ----")
    for row in rows:
        logger.debug(row)
        content = {'mensagem': row[0], 'data': row[1], 'leilaoid': row[2], 'utilizadorid': row[3]}
        payload.append(content) # appending to the payload to be returned

    conn.close()
    return jsonify(payload)  

## GET todas as notificacoes

@app.route("/dbproj/notificacoes/", methods=['GET'], strict_slashes=True)
def get_all_notificacoes():
    
    payload = request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    #INSERT lista de murais dos leilões
    cur.execute("SELECT mensagem, data, utilizadorid FROM notificacao")
    rows = cur.fetchall()

    payload = []
    for row in rows:
        logger.debug(row)
        content = {'mensagem': row[0], 'data': row[1], 'utilizadorid': row[2]}
        payload.append(content) # appending to the payload to be returned

    conn.close()
    return jsonify(payload)  


#devolve string com a data e hora
def timeStamp(data, hora):
    return data + " " + hora + ":00 GMT"

#devolve o string com o Like preenchido
def like(str, tipo):
    # '%str'
    if tipo == 0:
        return "%" + str
    # 'str%'    
    elif tipo == 1:
        return str + "%"
    # '%str%' 
    return "%" + str + "%"   


##########################################################
## DATABASE ACCESS
##########################################################

def db_connection():
    db = psycopg2.connect(user = os.getenv('user_db'),
                            password = os.getenv('password_db'),
                            host = "db",
                            port = "5432",
                            database = "dbprojeto")
    return db


##########################################################
## MAIN
##########################################################
if __name__ == "__main__":

    # Set up the logging
    logging.basicConfig(filename="logs/log_file.log")
    logger = logging.getLogger('logger')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s]:  %(message)s',
                              '%H:%M:%S')
                              # "%Y-%m-%d %H:%M:%S") # not using DATE to simplify
    ch.setFormatter(formatter)
    logger.addHandler(ch)


    time.sleep(1) # just to let the DB start before this print :-)


    logger.info("\n---------------------------------------------------------------\n" + 
                  "API v1.0 online: http://localhost:8080/dbproj/\n\n")


    

    app.run(host="0.0.0.0", debug=True, threaded=True)

