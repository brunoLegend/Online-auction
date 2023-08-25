CREATE TABLE utilizador (
	utilizadorid 		SERIAL,
	authToken			INT,
	data_expiracao		TIMESTAMP,
	username 			VARCHAR(512) UNIQUE NOT NULL,
	password 			VARCHAR(512) NOT NULL,
	email	 			VARCHAR(512) UNIQUE NOT NULL,
	ban		 			BOOL NOT NULL,
	isadmin	 			BOOL NOT NULL,
	PRIMARY KEY(utilizadorid)
);

CREATE TABLE artigo (
	codigo	 			BIGINT,
	nome	 			VARCHAR(512) UNIQUE NOT NULL,
	descricao 			VARCHAR(512) NOT NULL,
	vendido	 			BOOL NOT NULL,
	PRIMARY KEY(codigo)
);

CREATE TABLE leilao (
	leilaoid		 	SERIAL,
	fim			 		TIMESTAMP NOT NULL,
	inicio				TIMESTAMP NOT NULL,
	titulo			 	VARCHAR(512) NOT NULL,
	descricao		 	VARCHAR(512) NOT NULL,
	cancelado		 	BOOL NOT NULL,
	precomin		 	FLOAT(8) NOT NULL,
	licitacaomaior		FLOAT(8),
	artigo_codigo		BIGINT NOT NULL,
	utilizadorid 		BIGINT NOT NULL,
	PRIMARY KEY(leilaoid)
);

CREATE TABLE licitacao (
	licitacaoid			SERIAL,
	valido				BOOL NOT NULL,
	data		 		TIMESTAMP NOT NULL,
	valor		 		FLOAT(8) NOT NULL,
	leilaoid	 		BIGINT NOT NULL,
	utilizadorid 		BIGINT NOT NULL,
	PRIMARY KEY(licitacaoid)
);

CREATE TABLE versoesant (
	versaoid	 		SERIAL,
	titulo		 		VARCHAR(512),
	descricao	 		VARCHAR(512),
	data		 		TIMESTAMP NOT NULL,
	leilaoid 			BIGINT NOT NULL,
	PRIMARY KEY(versaoid)
);

CREATE TABLE mural (
	mensagemid		 	SERIAL,
	mensagem		 	VARCHAR(512) NOT NULL,
	data			 	TIMESTAMP NOT NULL,
	leilaoid	 		BIGINT NOT NULL,
	utilizadorid 		BIGINT NOT NULL,
	PRIMARY KEY(mensagemid)
);

CREATE TABLE notificacao (
	notificacaoid		SERIAL,
	mensagem			VARCHAR(512),
	data			 	TIMESTAMP NOT NULL,
	recebida		 	BOOL NOT NULL,
	utilizadorid 		BIGINT NOT NULL,
	PRIMARY KEY(notificacaoid)
);

--Funcoes chamadas pelos TRIGGERS
CREATE FUNCTION registar_leilao_function() RETURNS TRIGGER
   	LANGUAGE PLPGSQL
AS $$

BEGIN
	
	--verificar se não ha nenhum leilao com o mesmo artigo
	--caso haja, o leilao tem de ter acabado e o artigo nao deve ter sido vendido
	IF EXISTS(SELECT * FROM leilao AS l WHERE l.artigo_codigo = NEW.artigo_codigo AND l.cancelado = false AND ( (l.fim >= NOW() + INTERVAL '1' HOUR) OR (l.fim <= NOW() + INTERVAL '1' HOUR AND l.licitacaomaior > 0) ) ) THEN
		RAISE EXCEPTION 'O leilão não pode ser criado por causa do artigo escolhido!';
	END IF;

	RETURN NEW;

END;
$$;


CREATE FUNCTION nova_mensagem_function() RETURNS TRIGGER
   	LANGUAGE PLPGSQL
AS $$

DECLARE
	temprow record;

BEGIN

	FOR temprow IN
        SELECT DISTINCT ON (utilizadorid) utilizadorid, leilaoid FROM mural WHERE leilaoid = NEW.leilaoid 
    LOOP
        INSERT INTO notificacao (mensagem, data, recebida, utilizadorid) VALUES (CONCAT('Nova mensagem no Mural do leilao: ', NEW.leilaoid , '. Mensagem: ', NEW.mensagem), NEW.data, false, temprow.utilizadorid);
    END LOOP;

	RETURN NEW;

END;
$$;


CREATE FUNCTION editar_leilao_function() RETURNS TRIGGER
       LANGUAGE PLPGSQL
AS $$

DECLARE
    temprow record;
	
BEGIN

	--cancelar leilao
    IF NEW.cancelado != OLD.cancelado THEN
		FOR temprow IN
            SELECT utilizadorid FROM licitacao WHERE leilaoid = NEW.leilaoid AND valido = true AND valor != NEW.licitacaomaior
			UNION 
			SELECT utilizadorid FROM leilao WHERE leilaoid = NEW.leilaoid
			UNION 
			SELECT utilizadorid FROM mural WHERE leilaoid = NEW.leilaoid
		LOOP
            INSERT INTO notificacao (mensagem, data, recebida, utilizadorid) 
			VALUES (CONCAT('leilao cancelado: ', NEW.leilaoid, '. Com o titulo: ', NEW.titulo), NOW() + INTERVAL '1' HOUR, false, temprow.utilizadorid);
        END LOOP;

	--nova licitacao
	ELSIF NEW.licitacaomaior != OLD.licitacaomaior THEN
        FOR temprow IN
            SELECT utilizadorid FROM licitacao WHERE leilaoid = NEW.leilaoid AND valido = true AND valor != NEW.licitacaomaior
			UNION 
			SELECT utilizadorid FROM leilao WHERE leilaoid = NEW.leilaoid
		LOOP
            INSERT INTO notificacao (mensagem, data, recebida, utilizadorid) 
			VALUES (CONCAT('nova licitacao maior no leilao: ', NEW.leilaoid, ', Com o valor: ', NEW.licitacaomaior, '. Pelo username: ', 
																		(SELECT username FROM utilizador WHERE utilizadorid = (SELECT utilizadorid FROM licitacao WHERE licitacao.leilaoid = NEW.leilaoid AND valor = NEW.licitacaomaior AND valido = true)))
																		, NOW() + INTERVAL '1' HOUR, false, temprow.utilizadorid);
        END LOOP;

	--editar texto de um leilao
    ELSIF NEW.titulo != OLD.titulo OR NEW.descricao != OLD.descricao THEN

        INSERT INTO versoesant (titulo, descricao, data, leilaoid) VALUES (OLD.titulo, OLD.descricao, NOW() + INTERVAL '1' HOUR,  NEW.leilaoid);
    
	END IF;

    RETURN NEW;

END;
$$;


CREATE FUNCTION editar_utilizador_function() RETURNS TRIGGER
       LANGUAGE PLPGSQL
AS $$

DECLARE
    temprow record;

BEGIN

    --utilizador banido
	IF NEW.ban != OLD.ban THEN
        
		--banir leiloes
		FOR temprow IN
            SELECT leilaoid FROM leilao WHERE utilizadorid = NEW.utilizadorid AND fim > NOW() + INTERVAL '1' HOUR AND cancelado = false
        LOOP
            UPDATE leilao SET cancelado = true WHERE leilaoid = temprow.leilaoid;
        END LOOP;

		--cancelar licitacoes
		FOR temprow IN
            SELECT licitacaoid, leilaoid, valor FROM licitacao WHERE utilizadorid = NEW.utilizadorid AND leilaoid IN (SELECT leilaoid FROM leilao WHERE fim > NOW() + INTERVAL '1' HOUR AND cancelado = false)
        LOOP
            UPDATE licitacao 
				SET valido = false 
				WHERE licitacaoid = temprow.licitacaoid;
			
			UPDATE leilao 
				SET licitacaomaior = (SELECT COALESCE(MAX(valor), 0) 
										FROM licitacao 
										WHERE leilaoid = temprow.leilaoid AND valido = true);
			
			INSERT INTO mural (mensagem, data, leilaoid, utilizadorid) 
				VALUES (CONCAT('Houve uma licitação cancelada no leilao:', temprow.leilaoid ,', username da pessoa: ', NEW.username), NOW + INTERVAL '1' HOUR, temprow.leilaoid, null);
        END LOOP;

    END IF;

    RETURN NEW;

END;
$$;

--TRIGGERS
CREATE TRIGGER trig1
   	BEFORE INSERT ON leilao
  	FOR EACH ROW
       EXECUTE PROCEDURE registar_leilao_function();

CREATE TRIGGER trig2
   	AFTER INSERT ON mural
  	FOR EACH ROW
       EXECUTE PROCEDURE nova_mensagem_function();

CREATE TRIGGER trig3
   	AFTER UPDATE ON leilao
  	FOR EACH ROW
       EXECUTE PROCEDURE editar_leilao_function();

CREATE TRIGGER trig4
   	AFTER UPDATE ON utilizador
  	FOR EACH ROW
       EXECUTE PROCEDURE editar_utilizador_function();	   


ALTER TABLE leilao ADD CONSTRAINT leilao_fk1 FOREIGN KEY (artigo_codigo) REFERENCES artigo(codigo);
ALTER TABLE leilao ADD CONSTRAINT leilao_fk2 FOREIGN KEY (utilizadorid) REFERENCES utilizador(utilizadorid);
ALTER TABLE licitacao ADD CONSTRAINT licitacao_fk1 FOREIGN KEY (leilaoid) REFERENCES leilao(leilaoid);
ALTER TABLE licitacao ADD CONSTRAINT licitacao_fk2 FOREIGN KEY (utilizadorid) REFERENCES utilizador(utilizadorid);
ALTER TABLE versoesant ADD CONSTRAINT versoesant_fk1 FOREIGN KEY (leilaoid) REFERENCES leilao(leilaoid);
ALTER TABLE mural ADD CONSTRAINT mural_fk1 FOREIGN KEY (leilaoid) REFERENCES leilao(leilaoid);
ALTER TABLE mural ADD CONSTRAINT mural_fk2 FOREIGN KEY (utilizadorid) REFERENCES utilizador(utilizadorid);
ALTER TABLE notificacao ADD CONSTRAINT notificacao_fk1 FOREIGN KEY (utilizadorid) REFERENCES utilizador(utilizadorid);


-- adicionar utilizadores
INSERT INTO utilizador (authToken, username, password, email, ban, isadmin)
VALUES 	(null, 'ola', 'ola', 'email_ola', false, false),
		(null, 'ola2', 'ola2', 'email_ola2', false, false),
		(null, 'ola3', 'ola3', 'email_ola3', false, false),
		(null, 'ola4', 'ola4', 'email_ola4', false, false),
		(null, 'ola5', 'ola5', 'email_ola5', false, false),
		(null, 'admin', 'admin', 'email_admin', false, true),		-- adicionar admin
		(null, 'admin2', 'admin2', 'email_admin2', false, true);	-- adicionar admin

-- adicionar artigos
INSERT INTO artigo (codigo, nome, descricao, vendido)
VALUES 	(1000000001, 'artigo1', 'desc1', false),
		(1000000002, 'artigo2', 'desc2', false),
		(1000000003, 'artigo3', 'desc3', false),
		(1000000004, 'artigo4', 'desc4', false),
		(1000000005, 'artigo5', 'desc5', false),
		(1000000006, 'artigo6', 'desc6', false);

-- adicionar leiloes
INSERT INTO leilao (inicio, fim, titulo, descricao, cancelado, precomin, licitacaomaior, artigo_codigo, utilizadorid) 
VALUES 	('2021-05-02 21:30:00', '2021-06-02 21:30:00', 'Relogio rolex como novo', 'Esta a venda', false, 10, 0, 1000000001, 1),
		('2021-05-02 21:30:00', '2021-06-02 21:30:00', 'Relogio rolex como novo2', 'Esta a venda2', false, 10, 0, 1000000002, 2),
		('2021-05-02 21:30:00', '2021-05-27 21:30:00', 'Relogio rolex como novo3', 'Esta a venda3', false, 10, 0, 1000000003, 3),
		('2021-05-02 21:30:00', '2021-05-21 21:30:00', 'Relogio rolex como novo4', 'Esta a venda4', false, 10, 0, 1000000004, 4),
		('2021-05-02 21:30:00', '2021-05-21 21:30:00', 'Relogio rolex como novo5', 'Esta a venda5', false, 10, 0, 1000000005, 5);

--adicionar mensagens ao Mural		
INSERT INTO mural (mensagem, data, leilaoid, utilizadorid)
VALUES	('nao comprem1', '2021-05-27 21:30:00', 1, 1);
INSERT INTO mural (mensagem, data, leilaoid, utilizadorid)			
VALUES	('nao comprem2', '2021-05-27 21:30:00', 2, 3);
INSERT INTO mural (mensagem, data, leilaoid, utilizadorid)			
VALUES	('nao comprem3', '2021-05-27 21:30:00', 3, 5);
INSERT INTO mural (mensagem, data, leilaoid, utilizadorid)				
VALUES 	('nao comprem4', '2021-05-27 21:30:00', 4, 1);
INSERT INTO mural (mensagem, data, leilaoid, utilizadorid)	
VALUES	('nao comprem5', '2021-05-27 21:30:00', 1, 2);	

--adicionar licitações ao leilao
--INSERT INTO licitacao (valido, data, valor, leilaoid, utilizadorid)	
--VALUES 	(true, '2021-05-27 21:30:00', 10, 1, 2);
--INSERT INTO licitacao (valido, data, valor, leilaoid, utilizadorid)
--VALUES	(true, '2021-05-27 21:30:00', 10, 1, 3);	
