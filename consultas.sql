USE achados_perdidos;

-- Consulta 1: Listar objetos encontrados do mais recente ao mais antigo
SELECT nome, categoria,data_registro
FROM Objeto
WHERE estatus = 'Encontrado'
ORDER BY data_registro DESC;

-- Consulta 2: Contar quantos objetos existem com cada status
SELECT estatus, COUNT(*) AS total_objetos
FROM Objeto
GROUP BY estatus;

-- Consulta 3: Quais pessoas nunca registraram um objeto?
SELECT nome 
FROM Pessoa
WHERE id_pessoa NOT IN(
		SELECT id_pessoa
        FROM Objeto
        );
        
-- Consulta 4: Relatório completo de devoluções (Objeto, quem retirou, funcionário que entregou)
SELECT d.data_devolucao, o.nome AS objeto , p.nome AS quem_retirou, p_func.nome AS funcionario_responsavel
FROM Devolucao d
	INNER JOIN Objeto o ON d.codigo_objeto = o.codigo
    INNER JOIN Pessoa p ON d.id_pessoa = p.id_pessoa
    INNER JOIN Funcionario f ON d.id_funcionario = f.id_funcionario
    INNER JOIN Pessoa p_func ON f.id_pessoa = p_func.id_pessoa;
    
-- Consulta 5: Quantos objetos foram registrados por Campus?
SELECT c.nome AS CAMPUS, COUNT(o.codigo) AS total_objetos
FROM Campus c 
	LEFT JOIN Local l ON c.codigo_campus = l.codigo_campus
    LEFT JOIN Objeto o ON l.id_local = o.id_local
GROUP BY c.codigo_campus, c.nome;

-- Consulta 6: Listar todos os objetos que ainda não foram devolvidos
SELECT o.nome AS objeto, l.predio, c.nome AS campus
FROM Objeto o
	INNER JOIN Local l ON o.id_local = l.id_local
    INNER JOIN Campus c ON l.codigo_campus = c.codigo_campus
WHERE o.estatus != 'Devolvido';

-- Consulta 7: Listar nome, e-mail e matricula de todos os alunos cadastrados
SELECT p.nome, p.email, a.matricula
FROM Pessoa p
	INNER JOIN Aluno a ON p.id_pessoa = a.id_pessoa;


