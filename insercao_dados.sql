-- Campus
INSERT INTO Campus(nome, endereco) VALUES
('Campus Anglo', 'Rua Gomes Carneiro, 1'),
('Campus I', 'Rua Almirante Barroso, 1202');

-- Pessoas
INSERT INTO Pessoa(nome, email, telefone, cpf) VALUES
('João Silva', 'joao.silva@email.com', '53999990001', '111.111.111-11'),
('Maria Oliveira', 'maria.oliveira@email.com', '53999990002', '222.222.222-22'),
('Pedro Santos', 'pedro.santos@email.com', '53999990003', '333.333.333-33'),
('Carla Pereira', 'carla.pereira@email.com', '53999990004', '444.444.444-44'),
('Lucas Mendes', 'lucas.mendes@email.com', '53999990005', '555.555.555-55'),
('Fernanda Costa', 'fernanda.costa@email.com', '53999990006', '666.666.666-66');

INSERT INTO Aluno(id_pessoa, matricula) VALUES
(1, '20240001'),
(2, '20240002'),
(3, '20240003');

INSERT INTO Funcionario(id_pessoa, id_funcionario) VALUES
(4, 'FUNC001'),
(5, 'FUNC002');

INSERT INTO Professor(id_pessoa, siape) VALUES
(6, 'SIAPE12345');

-- Locais
INSERT INTO Local(tipo_local, andar, predio, numero_sala, codigo_campus) VALUES
('Lab 3', 3, 'Bloco A', '336', 1),
('Sala de Aula', 4, 'Bloco A', '437', 1),
('Banheiro Feminino', 1, 'Bloco principal', NULL, 2),
('Estacionamento', NULL, NULL, NULL, 1);

-- Objetos
INSERT INTO Objeto(nome, categoria, foto, estatus, data_registro, id_local, id_pessoa) VALUES
('Garrafa Térmica Preta', 'Itens pessoais', '/fotos/garrafa.jpg', 'Encontrado', '2026-11-10 09:30:00', 1, 1),
('Carregador de Notebook', 'Eletrônico', '/fotos/carregador.jpg', 'Encontrado', '2026-09-11 14:15:00', 2, 6),
('Caderno Espiral Azul', 'Material Escolar', '/fotos/caderno.jpg', 'Encontrado', '2026-10-06 16:40:00', 1, 2),
('Casaco de Moletom Cinza', 'Vestuário', '/fotos/casaco.jpg', 'Encontrado', '2026-08-13 11:00:00', 3, 4),
('Chaveiro com 3 chaves', 'Acessório', NULL, 'Perdido', '2026-11-14 18:20:00', 4, 3);

-- Devoluções (o trigger passa os objetos 2 e 4 para 'Devolvido')
INSERT INTO Devolucao(data_devolucao, codigo_objeto, id_pessoa, id_funcionario) VALUES
('2026-11-12 10:00:00', 2, 1, 'FUNC001'),
('2026-11-15 15:30:00', 4, 2, 'FUNC002');
