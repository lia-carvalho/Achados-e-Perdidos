USE achados_perdidos;

-- Consulta 1: Listar objetos encontrados do mais recente ao mais antigo
SELECT nome, categoria, data_registro
FROM Objeto
WHERE estatus = 'Encontrado'
ORDER BY data_registro DESC;

-- Consulta 2: Contar quantos objetos existem com cada status
SELECT estatus, COUNT(*) AS total_objetos
FROM Objeto
GROUP BY estatus;

-- Consulta 3: Quais pessoas nunca registraram um objeto?
-- (NOT EXISTS em vez de NOT IN: não quebra se houver id_pessoa NULL)
SELECT p.nome
FROM Pessoa p
WHERE NOT EXISTS (
    SELECT 1
    FROM Objeto o
    WHERE o.id_pessoa = p.id_pessoa
);

-- Consulta 4: Relatório completo de devoluções (objeto, quem retirou, funcionário que entregou)
SELECT d.data_devolucao, o.nome AS objeto, p.nome AS quem_retirou, p_func.nome AS funcionario_responsavel
FROM Devolucao d
    INNER JOIN Objeto o ON d.codigo_objeto = o.codigo
    INNER JOIN Pessoa p ON d.id_pessoa = p.id_pessoa
    INNER JOIN Funcionario f ON d.id_funcionario = f.id_funcionario
    INNER JOIN Pessoa p_func ON f.id_pessoa = p_func.id_pessoa
ORDER BY d.data_devolucao DESC;

-- Consulta 5: Quantos objetos foram registrados por Campus?
SELECT c.nome AS campus, COUNT(o.codigo) AS total_objetos
FROM Campus c
    LEFT JOIN Local l ON c.codigo_campus = l.codigo_campus
    LEFT JOIN Objeto o ON l.id_local = o.id_local
GROUP BY c.codigo_campus, c.nome;

-- Consulta 6: Listar todos os objetos que ainda não foram devolvidos
-- (inclui status e tipo de local, pois há locais sem prédio, como o estacionamento)
SELECT o.nome AS objeto, o.estatus, l.tipo_local, l.predio, c.nome AS campus
FROM Objeto o
    LEFT JOIN Local l ON o.id_local = l.id_local
    LEFT JOIN Campus c ON l.codigo_campus = c.codigo_campus
WHERE o.estatus <> 'Devolvido';

-- Consulta 7: Listar nome, e-mail e matrícula de todos os alunos cadastrados
SELECT p.nome, p.email, a.matricula
FROM Pessoa p
    INNER JOIN Aluno a ON p.id_pessoa = a.id_pessoa;

-- Consulta 8: Histórico de mudanças de status dos objetos (alimentado pelos triggers)
SELECT h.data_alteracao, h.codigo_objeto, o.nome AS objeto,
       h.status_anterior, h.status_novo, h.usuario
FROM Historico_Status h
    LEFT JOIN Objeto o ON o.codigo = h.codigo_objeto
ORDER BY h.data_alteracao DESC, h.id_historico DESC;
