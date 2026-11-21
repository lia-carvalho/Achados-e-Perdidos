DROP DATABASE IF EXISTS achados_perdidos;
CREATE DATABASE achados_perdidos;
USE achados_perdidos;

CREATE TABLE Campus(
	codigo_campus INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL,
    endereco VARCHAR(200)
);

CREATE TABLE Pessoa(
	id_pessoa INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    email VARCHAR(100),
    telefone VARCHAR (20),
    cpf VARCHAR (14)
);

CREATE TABLE Aluno(
	id_pessoa INT PRIMARY KEY,
	matricula VARCHAR(20) UNIQUE,
	FOREIGN KEY (id_pessoa) REFERENCES Pessoa(id_pessoa)
);

CREATE TABLE Professor(
	id_pessoa INT PRIMARY KEY,
    siape VARCHAR(20) UNIQUE,
    FOREIGN KEY (id_pessoa) REFERENCES Pessoa(id_pessoa)
);

CREATE TABLE Funcionario(
	id_pessoa INT PRIMARY KEY,
    id_funcionario VARCHAR(20) UNIQUE,
    FOREIGN KEY (id_pessoa) REFERENCES Pessoa(id_pessoa)
);

CREATE TABLE Local(
	id_local INT AUTO_INCREMENT PRIMARY KEY,
    tipo_local VARCHAR(50),
    andar INT,
    predio VARCHAR(50),
    numero_sala VARCHAR(10),
    codigo_campus INT,
    FOREIGN KEY (codigo_campus) REFERENCES Campus(codigo_campus)
);

CREATE TABLE Objeto(
	codigo INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    foto VARCHAR(250),
    estatus ENUM('Perdido', 'Encontrado', 'Devolvido') NOT NULL,
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_local INT,
    id_pessoa INT,
    FOREIGN KEY (id_local) REFERENCES Local(id_local),
	FOREIGN KEY (id_pessoa) REFERENCES Pessoa(id_pessoa)
);

CREATE TABLE Devolucao(
	id_devolucao INT AUTO_INCREMENT PRIMARY KEY,
    data_devolucao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    codigo_objeto INT,
    id_pessoa INT,
    id_funcionario VARCHAR(20),
    FOREIGN KEY (codigo_objeto) REFERENCES Objeto(codigo),
    FOREIGN KEY (id_pessoa) REFERENCES Pessoa(id_pessoa),
    FOREIGN KEY (id_funcionario) REFERENCES Funcionario(id_funcionario)
);



