USE achados_perdidos;

DROP TRIGGER IF EXISTS trg_devolucao_valida;
DROP TRIGGER IF EXISTS trg_devolucao_atualiza_status;
DROP TRIGGER IF EXISTS trg_devolucao_bloqueia_exclusao;
DROP TRIGGER IF EXISTS trg_objeto_valida_status;
DROP TRIGGER IF EXISTS trg_objeto_log_insert;
DROP TRIGGER IF EXISTS trg_objeto_log_update;

DELIMITER $$

-- Trigger 1: valida a devolução antes de gravar
--   * o objeto precisa existir e estar com status 'Encontrado'
--   * o funcionário não pode devolver o objeto para si mesmo

CREATE TRIGGER trg_devolucao_valida
BEFORE INSERT ON Devolucao
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(20);
    DECLARE v_pessoa_func INT;

    SET v_status = (SELECT estatus FROM Objeto WHERE codigo = NEW.codigo_objeto);

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Devolucao recusada: objeto inexistente.';
    ELSEIF v_status <> 'Encontrado' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Devolucao recusada: so e possivel devolver objetos com status Encontrado.';
    END IF;

    SET v_pessoa_func = (SELECT id_pessoa FROM Funcionario
                         WHERE id_funcionario = NEW.id_funcionario);

    IF v_pessoa_func = NEW.id_pessoa THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Devolucao recusada: o funcionario nao pode retirar o objeto para si mesmo.';
    END IF;
END$$

-- Trigger 2: após registrar a devolução, muda o objeto para 'Devolvido'
CREATE TRIGGER trg_devolucao_atualiza_status
AFTER INSERT ON Devolucao
FOR EACH ROW
BEGIN
    UPDATE Objeto
       SET estatus = 'Devolvido'
     WHERE codigo = NEW.codigo_objeto;
END$$

-- Trigger 3: devoluções são registro histórico, não podem ser apagadas
CREATE TRIGGER trg_devolucao_bloqueia_exclusao
BEFORE DELETE ON Devolucao
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Exclusao recusada: devolucoes sao registros historicos.';
END$$

-- Trigger 4: regras de mudança de status do objeto
--   * objeto 'Devolvido' não pode voltar a outro status
--   * só pode virar 'Devolvido' se existir uma devolução registrada

CREATE TRIGGER trg_objeto_valida_status
BEFORE UPDATE ON Objeto
FOR EACH ROW
BEGIN
    IF OLD.estatus = 'Devolvido' AND NEW.estatus <> 'Devolvido' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Alteracao recusada: objeto ja devolvido nao pode ser reaberto.';
    END IF;

    IF NEW.estatus = 'Devolvido' AND OLD.estatus <> 'Devolvido'
       AND NOT EXISTS (SELECT 1 FROM Devolucao WHERE codigo_objeto = NEW.codigo) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Alteracao recusada: para marcar como Devolvido registre uma devolucao.';
    END IF;
END$$

-- Trigger 5: auditoria - registra o status inicial do objeto

CREATE TRIGGER trg_objeto_log_insert
AFTER INSERT ON Objeto
FOR EACH ROW
BEGIN
    INSERT INTO Historico_Status (codigo_objeto, status_anterior, status_novo, usuario)
    VALUES (NEW.codigo, NULL, NEW.estatus, CURRENT_USER());
END$$

-- Trigger 6: auditoria - registra cada mudança de status

CREATE TRIGGER trg_objeto_log_update
AFTER UPDATE ON Objeto
FOR EACH ROW
BEGIN
    IF OLD.estatus <> NEW.estatus THEN
        INSERT INTO Historico_Status (codigo_objeto, status_anterior, status_novo, usuario)
        VALUES (NEW.codigo, OLD.estatus, NEW.estatus, CURRENT_USER());
    END IF;
END$$

DELIMITER ;
