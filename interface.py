import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import mysql.connector

STATUS_VALIDOS = ("Perdido", "Encontrado", "Devolvido")

# tipo de vínculo -> (tabela, coluna do identificador, rótulo)
VINCULOS = {
    "Aluno": ("Aluno", "matricula"),
    "Professor": ("Professor", "siape"),
    "Funcionário": ("Funcionario", "id_funcionario"),
}

CONSULTAS = {
    "1 - Objetos encontrados (mais recentes primeiro)": """
        SELECT nome, categoria, data_registro
        FROM Objeto
        WHERE estatus = 'Encontrado'
        ORDER BY data_registro DESC""",
    "2 - Total de objetos por status": """
        SELECT estatus, COUNT(*) AS total_objetos
        FROM Objeto
        GROUP BY estatus""",
    "3 - Pessoas que nunca registraram um objeto": """
        SELECT p.nome
        FROM Pessoa p
        WHERE NOT EXISTS (SELECT 1 FROM Objeto o WHERE o.id_pessoa = p.id_pessoa)""",
    "4 - Relatório de devoluções": """
        SELECT d.data_devolucao, o.nome AS objeto, p.nome AS quem_retirou,
               p_func.nome AS funcionario_responsavel
        FROM Devolucao d
            INNER JOIN Objeto o ON d.codigo_objeto = o.codigo
            INNER JOIN Pessoa p ON d.id_pessoa = p.id_pessoa
            INNER JOIN Funcionario f ON d.id_funcionario = f.id_funcionario
            INNER JOIN Pessoa p_func ON f.id_pessoa = p_func.id_pessoa""",
    "5 - Objetos registrados por campus": """
        SELECT c.nome AS campus, COUNT(o.codigo) AS total_objetos
        FROM Campus c
            LEFT JOIN Local l ON c.codigo_campus = l.codigo_campus
            LEFT JOIN Objeto o ON l.id_local = o.id_local
        GROUP BY c.codigo_campus, c.nome""",
    "6 - Objetos ainda não devolvidos": """
        SELECT o.nome AS objeto, o.estatus, l.tipo_local, l.predio, c.nome AS campus
        FROM Objeto o
            LEFT JOIN Local l ON o.id_local = l.id_local
            LEFT JOIN Campus c ON l.codigo_campus = c.codigo_campus
        WHERE o.estatus <> 'Devolvido'""",
    "7 - Alunos cadastrados": """
        SELECT p.nome, p.email, a.matricula
        FROM Pessoa p
            INNER JOIN Aluno a ON p.id_pessoa = a.id_pessoa""",
    "8 - Histórico de status (auditoria)": """
        SELECT h.data_alteracao, h.codigo_objeto, o.nome AS objeto,
               h.status_anterior, h.status_novo, h.usuario
        FROM Historico_Status h
            LEFT JOIN Objeto o ON o.codigo = h.codigo_objeto
        ORDER BY h.data_alteracao DESC, h.id_historico DESC""",
}


def conectar():
    """Pede os dados de conexão e devolve uma conexão MySQL (ou None)."""
    raiz = tk.Tk()
    raiz.withdraw()
    try:
        while True:
            host = simpledialog.askstring("Conexão", "Host:", initialvalue="localhost", parent=raiz)
            if host is None:
                return None
            usuario = simpledialog.askstring("Conexão", "Usuário:", initialvalue="root", parent=raiz)
            if usuario is None:
                return None
            senha = simpledialog.askstring("Conexão", "Senha:", show="*", parent=raiz)
            if senha is None:
                return None
            try:
                return mysql.connector.connect(
                    host=host, user=usuario, password=senha,
                    database="achados_perdidos", autocommit=True,
                )
            except mysql.connector.Error as e:
                messagebox.showerror("Erro de conexão", str(e), parent=raiz)
    finally:
        raiz.destroy()


def normalizar(valor):
    """Minúsculas e sem acentos, para a pesquisa ignorar maiúsculas/acentos."""
    texto = "" if valor is None else str(valor)
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower()


class App(tk.Tk):
    def __init__(self, conn):
        super().__init__()
        self.title("Achados e Perdidos")
        self.geometry("1050x700")
        self.conn = conn

        abas = ttk.Notebook(self)
        abas.pack(fill="both", expand=True)
        self.aba_obj = ttk.Frame(abas)
        self.aba_dev = ttk.Frame(abas)
        self.aba_pes = ttk.Frame(abas)
        self.aba_loc = ttk.Frame(abas)
        self.aba_con = ttk.Frame(abas)
        abas.add(self.aba_obj, text="Objetos")
        abas.add(self.aba_dev, text="Devoluções")
        abas.add(self.aba_pes, text="Pessoas")
        abas.add(self.aba_loc, text="Campus e Locais")
        abas.add(self.aba_con, text="Consultas")

        self.montar_objetos()
        self.montar_devolucoes()
        self.montar_pessoas()
        self.montar_locais()
        self.montar_consultas()
        self.atualizar_tudo()

    # Acesso ao banco
    def consultar(self, sql, params=()):
        cur = self.conn.cursor()
        try:
            cur.execute(sql, params)
            colunas = [c[0] for c in cur.description]
            return colunas, cur.fetchall()
        finally:
            cur.close()

    def executar(self, sql, params=()):
        """Executa INSERT/UPDATE/DELETE. Mostra o erro do banco (inclusive
        das mensagens dos triggers) e devolve True/False."""
        cur = self.conn.cursor()
        try:
            cur.execute(sql, params)
            return True
        except mysql.connector.Error as e:
            messagebox.showerror("Operação recusada", e.msg)
            return False
        finally:
            cur.close()

    # Tela
    @staticmethod
    def criar_tree(pai):
        quadro = ttk.Frame(pai)
        quadro.pack(fill="both", expand=True, padx=8, pady=4)
        tree = ttk.Treeview(quadro, show="headings", height=10)
        barra = ttk.Scrollbar(quadro, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=barra.set)
        tree.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        return tree

    @staticmethod
    def preencher(tree, colunas, linhas):
        tree["columns"] = colunas
        for c in colunas:
            tree.heading(c, text=c)
            tree.column(c, width=130, anchor="w")
        tree.delete(*tree.get_children())
        for linha in linhas:
            tree.insert("", "end", values=["" if v is None else v for v in linha])

    @staticmethod
    def id_do_combo(combo):
        texto = combo.get().strip()
        return texto.split(" - ", 1)[0] if texto else None

    @staticmethod
    def linha_form(form, linha, rotulo, widget):
        ttk.Label(form, text=rotulo).grid(row=linha, column=0, sticky="e", padx=4, pady=2)
        widget.grid(row=linha, column=1, sticky="w", padx=4, pady=2)
        return widget

    def atualizar_tudo(self):
        self.carregar_combos()
        self.carregar_objetos()
        self.carregar_devolucoes()
        self.carregar_pessoas()
        self.carregar_locais()

    def carregar_combos(self):
        _, locais = self.consultar("""
            SELECT l.id_local,
                   CONCAT(l.tipo_local, IFNULL(CONCAT(' / ', l.predio), ''),
                          IFNULL(CONCAT(' (', c.nome, ')'), ''))
            FROM Local l LEFT JOIN Campus c ON l.codigo_campus = c.codigo_campus
            ORDER BY l.id_local""")
        _, pessoas = self.consultar("SELECT id_pessoa, nome FROM Pessoa ORDER BY nome")
        _, campi = self.consultar("SELECT codigo_campus, nome FROM Campus ORDER BY nome")
        _, encontrados = self.consultar(
            "SELECT codigo, nome FROM Objeto WHERE estatus = 'Encontrado' ORDER BY codigo")
        _, funcionarios = self.consultar("""
            SELECT f.id_funcionario, p.nome
            FROM Funcionario f INNER JOIN Pessoa p ON f.id_pessoa = p.id_pessoa
            ORDER BY p.nome""")

        fmt = lambda linhas: [f"{a} - {b}" for a, b in linhas]
        self.cb_obj_local["values"] = fmt(locais)
        self.cb_loc_campus["values"] = fmt(campi)
        self.cb_obj_pessoa["values"] = fmt(pessoas)
        self.cb_dev_pessoa["values"] = fmt(pessoas)
        self.cb_dev_objeto["values"] = fmt(encontrados)
        self.cb_dev_func["values"] = fmt(funcionarios)
        for cb in (self.cb_dev_objeto, self.cb_dev_pessoa, self.cb_dev_func):
            cb.set("")

    # Objetos
    def montar_objetos(self):
        aba = self.aba_obj
        topo = ttk.Frame(aba)
        topo.pack(fill="x", padx=8, pady=6)
        ttk.Label(topo, text="Filtrar por status:").pack(side="left")
        self.filtro_status = ttk.Combobox(topo, values=("Todos",) + STATUS_VALIDOS,
                                          state="readonly", width=12)
        self.filtro_status.current(0)
        self.filtro_status.pack(side="left", padx=4)
        self.filtro_status.bind("<<ComboboxSelected>>", lambda e: self.carregar_objetos())
        ttk.Button(topo, text="Atualizar", command=self.atualizar_tudo).pack(side="left", padx=4)

        self.tree_obj = self.criar_tree(aba)

        acoes = ttk.LabelFrame(aba, text="Ações no objeto selecionado")
        acoes.pack(fill="x", padx=8, pady=4)
        ttk.Label(acoes, text="Novo status:").pack(side="left", padx=4)
        self.cb_novo_status = ttk.Combobox(acoes, values=("Perdido", "Encontrado"),
                                           state="readonly", width=12)
        self.cb_novo_status.current(1)
        self.cb_novo_status.pack(side="left", padx=4)
        ttk.Button(acoes, text="Alterar status", command=self.alterar_status).pack(side="left", padx=4)
        ttk.Button(acoes, text="Excluir objeto", command=self.excluir_objeto).pack(side="left", padx=4)

        form = ttk.LabelFrame(aba, text="Registrar novo objeto")
        form.pack(fill="x", padx=8, pady=6)
        self.e_obj_nome = self.linha_form(form, 0, "Nome:", ttk.Entry(form, width=40))
        self.e_obj_cat = self.linha_form(form, 1, "Categoria:", ttk.Entry(form, width=40))
        self.e_obj_foto = self.linha_form(form, 2, "Foto (caminho, opcional):", ttk.Entry(form, width=40))
        self.cb_obj_status = self.linha_form(
            form, 3, "Status:", ttk.Combobox(form, values=("Perdido", "Encontrado"),
                                             state="readonly", width=15))
        self.cb_obj_status.current(1)
        self.cb_obj_local = self.linha_form(form, 4, "Local:", ttk.Combobox(form, state="readonly", width=50))
        self.cb_obj_pessoa = self.linha_form(form, 5, "Registrado por:", ttk.Combobox(form, state="readonly", width=50))
        ttk.Button(form, text="Registrar objeto", command=self.registrar_objeto).grid(
            row=6, column=1, sticky="w", padx=4, pady=6)

    def carregar_objetos(self):
        sql = """
            SELECT o.codigo, o.nome, o.categoria, o.estatus, o.data_registro,
                   CONCAT(IFNULL(l.tipo_local, ''), IFNULL(CONCAT(' / ', l.predio), '')) AS local,
                   c.nome AS campus, p.nome AS registrado_por
            FROM Objeto o
                LEFT JOIN Local l ON o.id_local = l.id_local
                LEFT JOIN Campus c ON l.codigo_campus = c.codigo_campus
                LEFT JOIN Pessoa p ON o.id_pessoa = p.id_pessoa"""
        params = ()
        if self.filtro_status.get() != "Todos":
            sql += " WHERE o.estatus = %s"
            params = (self.filtro_status.get(),)
        sql += " ORDER BY o.data_registro DESC"
        colunas, linhas = self.consultar(sql, params)
        self.preencher(self.tree_obj, colunas, linhas)

    def objeto_selecionado(self):
        sel = self.tree_obj.selection()
        if not sel:
            messagebox.showinfo("Atenção", "Selecione um objeto na tabela.")
            return None
        return self.tree_obj.item(sel[0])["values"][0]

    def registrar_objeto(self):
        nome = self.e_obj_nome.get().strip()
        categoria = self.e_obj_cat.get().strip()
        if not nome or not categoria:
            messagebox.showwarning("Atenção", "Nome e categoria são obrigatórios.")
            return
        id_local = self.id_do_combo(self.cb_obj_local)
        id_pessoa = self.id_do_combo(self.cb_obj_pessoa)
        if not id_local or not id_pessoa:
            messagebox.showwarning("Atenção", "Escolha o local e quem está registrando.")
            return
        ok = self.executar(
            """INSERT INTO Objeto (nome, categoria, foto, estatus, id_local, id_pessoa)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (nome, categoria, self.e_obj_foto.get().strip() or None,
             self.cb_obj_status.get(), id_local, id_pessoa))
        if ok:
            for e in (self.e_obj_nome, self.e_obj_cat, self.e_obj_foto):
                e.delete(0, "end")
            self.atualizar_tudo()
            messagebox.showinfo("Pronto", "Objeto registrado.")

    def alterar_status(self):
        codigo = self.objeto_selecionado()
        if codigo is None:
            return
        if self.executar("UPDATE Objeto SET estatus = %s WHERE codigo = %s",
                         (self.cb_novo_status.get(), codigo)):
            self.atualizar_tudo()

    def excluir_objeto(self):
        codigo = self.objeto_selecionado()
        if codigo is None:
            return
        if messagebox.askyesno("Confirmar", f"Excluir o objeto {codigo}?"):
            if self.executar("DELETE FROM Objeto WHERE codigo = %s", (codigo,)):
                self.atualizar_tudo()

    # Devoluções
    def montar_devolucoes(self):
        aba = self.aba_dev
        self.tree_dev = self.criar_tree(aba)

        form = ttk.LabelFrame(aba, text="Registrar devolução (só objetos com status Encontrado)")
        form.pack(fill="x", padx=8, pady=6)
        self.cb_dev_objeto = self.linha_form(form, 0, "Objeto:", ttk.Combobox(form, state="readonly", width=50))
        self.cb_dev_pessoa = self.linha_form(form, 1, "Quem retira:", ttk.Combobox(form, state="readonly", width=50))
        self.cb_dev_func = self.linha_form(form, 2, "Funcionário responsável:", ttk.Combobox(form, state="readonly", width=50))
        ttk.Button(form, text="Registrar devolução", command=self.registrar_devolucao).grid(
            row=3, column=1, sticky="w", padx=4, pady=6)

    def carregar_devolucoes(self):
        colunas, linhas = self.consultar("""
            SELECT d.id_devolucao, d.data_devolucao, o.nome AS objeto,
                   p.nome AS quem_retirou, pf.nome AS funcionario
            FROM Devolucao d
                INNER JOIN Objeto o ON d.codigo_objeto = o.codigo
                INNER JOIN Pessoa p ON d.id_pessoa = p.id_pessoa
                INNER JOIN Funcionario f ON d.id_funcionario = f.id_funcionario
                INNER JOIN Pessoa pf ON f.id_pessoa = pf.id_pessoa
            ORDER BY d.data_devolucao DESC""")
        self.preencher(self.tree_dev, colunas, linhas)

    def registrar_devolucao(self):
        objeto = self.id_do_combo(self.cb_dev_objeto)
        pessoa = self.id_do_combo(self.cb_dev_pessoa)
        func = self.id_do_combo(self.cb_dev_func)
        if not (objeto and pessoa and func):
            messagebox.showwarning("Atenção", "Preencha objeto, quem retira e funcionário.")
            return
        if self.executar(
                "INSERT INTO Devolucao (codigo_objeto, id_pessoa, id_funcionario) VALUES (%s, %s, %s)",
                (objeto, pessoa, func)):
            self.atualizar_tudo()
            messagebox.showinfo("Pronto", "Devolução registrada. O objeto agora está como Devolvido.")

    # Pessoas
    def montar_pessoas(self):
        aba = self.aba_pes
        self.tree_pes = self.criar_tree(aba)

        form = ttk.LabelFrame(aba, text="Cadastrar pessoa")
        form.pack(fill="x", padx=8, pady=6)
        self.e_pes_nome = self.linha_form(form, 0, "Nome:", ttk.Entry(form, width=40))
        self.e_pes_email = self.linha_form(form, 1, "E-mail:", ttk.Entry(form, width=40))
        self.e_pes_tel = self.linha_form(form, 2, "Telefone:", ttk.Entry(form, width=40))
        self.e_pes_cpf = self.linha_form(form, 3, "CPF:", ttk.Entry(form, width=40))
        self.cb_pes_tipo = self.linha_form(
            form, 4, "Vínculo:", ttk.Combobox(form, values=list(VINCULOS) + ["Nenhum"],
                                              state="readonly", width=15))
        self.cb_pes_tipo.current(0)
        self.e_pes_ident = self.linha_form(
            form, 5, "Matrícula / SIAPE / ID funcionário:", ttk.Entry(form, width=40))
        ttk.Button(form, text="Cadastrar pessoa", command=self.cadastrar_pessoa).grid(
            row=6, column=1, sticky="w", padx=4, pady=6)

    def carregar_pessoas(self):
        colunas, linhas = self.consultar("""
            SELECT p.id_pessoa, p.nome, p.email, p.telefone, p.cpf,
                   CASE WHEN a.id_pessoa IS NOT NULL THEN 'Aluno'
                        WHEN pr.id_pessoa IS NOT NULL THEN 'Professor'
                        WHEN f.id_pessoa IS NOT NULL THEN 'Funcionário'
                        ELSE '-' END AS vinculo,
                   COALESCE(a.matricula, pr.siape, f.id_funcionario) AS identificador
            FROM Pessoa p
                LEFT JOIN Aluno a ON a.id_pessoa = p.id_pessoa
                LEFT JOIN Professor pr ON pr.id_pessoa = p.id_pessoa
                LEFT JOIN Funcionario f ON f.id_pessoa = p.id_pessoa
            ORDER BY p.id_pessoa""")
        self.preencher(self.tree_pes, colunas, linhas)

    def cadastrar_pessoa(self):
        nome = self.e_pes_nome.get().strip()
        tipo = self.cb_pes_tipo.get()
        ident = self.e_pes_ident.get().strip()
        if not nome:
            messagebox.showwarning("Atenção", "O nome é obrigatório.")
            return
        if tipo in VINCULOS and not ident:
            messagebox.showwarning("Atenção", "Informe o identificador do vínculo escolhido.")
            return

        cur = self.conn.cursor()
        try:
            self.conn.start_transaction()   # Pessoa + vínculo: tudo ou nada
            cur.execute(
                "INSERT INTO Pessoa (nome, email, telefone, cpf) VALUES (%s, %s, %s, %s)",
                (nome, self.e_pes_email.get().strip() or None,
                 self.e_pes_tel.get().strip() or None,
                 self.e_pes_cpf.get().strip() or None))
            id_pessoa = cur.lastrowid
            if tipo in VINCULOS:
                tabela, coluna = VINCULOS[tipo]   # nomes vêm do dicionário fixo
                cur.execute(f"INSERT INTO {tabela} (id_pessoa, {coluna}) VALUES (%s, %s)",
                            (id_pessoa, ident))
            self.conn.commit()
        except mysql.connector.Error as e:
            self.conn.rollback()
            messagebox.showerror("Operação recusada", e.msg)
            return
        finally:
            cur.close()

        for e in (self.e_pes_nome, self.e_pes_email, self.e_pes_tel, self.e_pes_cpf, self.e_pes_ident):
            e.delete(0, "end")
        self.atualizar_tudo()
        messagebox.showinfo("Pronto", "Pessoa cadastrada.")

    # Campus e Locais
    def montar_locais(self):
        aba = self.aba_loc

        quadro_campus = ttk.LabelFrame(aba, text="Campus")
        quadro_campus.pack(fill="both", expand=True, padx=8, pady=4)
        self.tree_campus = self.criar_tree(quadro_campus)
        self.tree_campus.configure(height=4)
        form_c = ttk.Frame(quadro_campus)
        form_c.pack(fill="x", padx=8, pady=4)
        ttk.Label(form_c, text="Nome:").pack(side="left")
        self.e_camp_nome = ttk.Entry(form_c, width=25)
        self.e_camp_nome.pack(side="left", padx=4)
        ttk.Label(form_c, text="Endereço:").pack(side="left")
        self.e_camp_end = ttk.Entry(form_c, width=40)
        self.e_camp_end.pack(side="left", padx=4)
        ttk.Button(form_c, text="Cadastrar campus", command=self.cadastrar_campus).pack(side="left", padx=6)

        quadro_local = ttk.LabelFrame(aba, text="Locais")
        quadro_local.pack(fill="both", expand=True, padx=8, pady=4)
        self.tree_loc = self.criar_tree(quadro_local)
        self.tree_loc.configure(height=6)
        form_l = ttk.Frame(quadro_local)
        form_l.pack(fill="x", padx=8, pady=4)
        self.e_loc_tipo = self.linha_form(form_l, 0, "Tipo (ex.: Sala de Aula):", ttk.Entry(form_l, width=30))
        self.e_loc_andar = self.linha_form(form_l, 1, "Andar (opcional):", ttk.Entry(form_l, width=10))
        self.e_loc_predio = self.linha_form(form_l, 2, "Prédio (opcional):", ttk.Entry(form_l, width=30))
        self.e_loc_sala = self.linha_form(form_l, 3, "Nº da sala (opcional):", ttk.Entry(form_l, width=10))
        self.cb_loc_campus = self.linha_form(form_l, 4, "Campus:", ttk.Combobox(form_l, state="readonly", width=40))
        ttk.Button(form_l, text="Cadastrar local", command=self.cadastrar_local).grid(
            row=5, column=1, sticky="w", padx=4, pady=6)

    def carregar_locais(self):
        colunas, linhas = self.consultar(
            "SELECT codigo_campus, nome, endereco FROM Campus ORDER BY codigo_campus")
        self.preencher(self.tree_campus, colunas, linhas)
        colunas, linhas = self.consultar("""
            SELECT l.id_local, l.tipo_local, l.andar, l.predio, l.numero_sala, c.nome AS campus
            FROM Local l INNER JOIN Campus c ON l.codigo_campus = c.codigo_campus
            ORDER BY l.id_local""")
        self.preencher(self.tree_loc, colunas, linhas)

    def cadastrar_campus(self):
        nome = self.e_camp_nome.get().strip()
        if not nome:
            messagebox.showwarning("Atenção", "O nome do campus é obrigatório.")
            return
        if self.executar("INSERT INTO Campus (nome, endereco) VALUES (%s, %s)",
                         (nome, self.e_camp_end.get().strip() or None)):
            self.e_camp_nome.delete(0, "end")
            self.e_camp_end.delete(0, "end")
            self.atualizar_tudo()
            messagebox.showinfo("Pronto", "Campus cadastrado.")

    def cadastrar_local(self):
        tipo = self.e_loc_tipo.get().strip()
        id_campus = self.id_do_combo(self.cb_loc_campus)
        if not tipo or not id_campus:
            messagebox.showwarning("Atenção", "Informe o tipo do local e escolha o campus.")
            return
        andar = self.e_loc_andar.get().strip()
        if andar:
            try:
                andar = int(andar)
            except ValueError:
                messagebox.showwarning("Atenção", "O andar precisa ser um número inteiro.")
                return
        if self.executar(
                """INSERT INTO Local (tipo_local, andar, predio, numero_sala, codigo_campus)
                   VALUES (%s, %s, %s, %s, %s)""",
                (tipo, andar if andar != "" else None,
                 self.e_loc_predio.get().strip() or None,
                 self.e_loc_sala.get().strip() or None,
                 id_campus)):
            for e in (self.e_loc_tipo, self.e_loc_andar, self.e_loc_predio, self.e_loc_sala):
                e.delete(0, "end")
            self.atualizar_tudo()
            messagebox.showinfo("Pronto", "Local cadastrado.")

    # Consultas (consulta pronta + filtro de pesquisa)
    def montar_consultas(self):
        aba = self.aba_con
        self.con_colunas = []
        self.con_linhas = []

        topo = ttk.Frame(aba)
        topo.pack(fill="x", padx=8, pady=6)
        ttk.Label(topo, text="Consulta:").pack(side="left")
        self.cb_consulta = ttk.Combobox(topo, values=list(CONSULTAS), state="readonly", width=50)
        self.cb_consulta.current(0)
        self.cb_consulta.pack(side="left", padx=4)
        ttk.Button(topo, text="Executar", command=self.executar_consulta).pack(side="left", padx=6)

        filtro = ttk.LabelFrame(aba, text="Filtro de pesquisa (aplicado ao resultado)")
        filtro.pack(fill="x", padx=8, pady=4)
        ttk.Label(filtro, text="Pesquisar:").pack(side="left", padx=4)
        self.var_busca = tk.StringVar()
        self.var_busca.trace_add("write", lambda *a: self.aplicar_filtro())
        self.e_busca = ttk.Entry(filtro, textvariable=self.var_busca, width=35)
        self.e_busca.pack(side="left", padx=4, pady=4)
        ttk.Label(filtro, text="em:").pack(side="left", padx=4)
        self.cb_busca_coluna = ttk.Combobox(filtro, state="readonly", width=22,
                                            values=("Todas as colunas",))
        self.cb_busca_coluna.current(0)
        self.cb_busca_coluna.pack(side="left", padx=4)
        self.cb_busca_coluna.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtro())
        ttk.Button(filtro, text="Limpar", command=self.limpar_filtro).pack(side="left", padx=6)
        self.lbl_contagem = ttk.Label(filtro, text="")
        self.lbl_contagem.pack(side="right", padx=8)

        self.tree_con = self.criar_tree(aba)

    def executar_consulta(self):
        try:
            colunas, linhas = self.consultar(CONSULTAS[self.cb_consulta.get()])
        except mysql.connector.Error as e:
            messagebox.showerror("Erro na consulta", e.msg)
            return
        self.con_colunas, self.con_linhas = colunas, linhas
        # recarrega as opções de coluna e zera o filtro para a nova consulta
        self.cb_busca_coluna["values"] = ("Todas as colunas",) + tuple(colunas)
        self.cb_busca_coluna.current(0)
        self.var_busca.set("")
        self.aplicar_filtro()

    def aplicar_filtro(self):
        """Filtra, em memória, as linhas da última consulta executada.
        Ignora maiúsculas/minúsculas e acentos; vários termos = todos precisam aparecer."""
        if not self.con_colunas:
            return
        termos = normalizar(self.var_busca.get()).split()
        escolha = self.cb_busca_coluna.get()
        if escolha in self.con_colunas:
            indices = [self.con_colunas.index(escolha)]
        else:
            indices = range(len(self.con_colunas))

        if termos:
            filtradas = []
            for linha in self.con_linhas:
                texto = " ".join(normalizar(linha[i]) for i in indices)
                if all(t in texto for t in termos):
                    filtradas.append(linha)
        else:
            filtradas = self.con_linhas

        self.preencher(self.tree_con, self.con_colunas, filtradas)
        self.lbl_contagem.config(text=f"{len(filtradas)} de {len(self.con_linhas)} registro(s)")

    def limpar_filtro(self):
        self.var_busca.set("")
        self.cb_busca_coluna.current(0)
        self.aplicar_filtro()


if __name__ == "__main__":
    conexao = conectar()
    if conexao is not None:
        App(conexao).mainloop()
        conexao.close()
