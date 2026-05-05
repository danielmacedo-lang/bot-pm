import discord
from discord.ext import commands, tasks
from discord.ui import View
from datetime import datetime
import json
import os
import asyncio

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TOKEN")

CANAL_BATE_PONTO = 1496930545308012589
CANAL_AUSENCIA = 1496930545308012590
CANAL_ANALISE = 1500831900640612522
CANAL_LOG_ACOES = 1496930545928769761
CANAL_PAINEL_ACOES = 1500846978760839218
CANAL_LOG_PRISAO = 1496930545928769762
CANAL_PAINEL_PRISAO = 1500856041758261438
CANAL_LOG_MULTAS = 1500859627133468823
CANAL_PAINEL_MULTAS = 1500859687862534144
CANAL_PROMOCAO = 1496930545308012591 
CANAL_ANALISE_PROMOCAO = 1500845768716845197
CANAL_RANKING = 1500879386381910022
CANAL_NOTIFICAR_PROMOCAO = 1496930545505009804
CANAL_REGISTRAR_ADVERTENCIA = 1501215075393077460
CANAL_ADVERTENCIAS = 1501212539734720532
CANAL_REGISTRO_WL = 1496930545308012586
CANAL_LOGS_WL = 1497654891496214799

# IDs dos cargos de patente (substitua 0 pelo ID real de cada cargo)
CARGO_ALUNO_ID = 1496930544808886314
CARGO_SOLDADO_ID = 1500864918709076149
CARGO_CABO_ID = 1500832275493818459
CARGO_SARGENTO_ID = 1500865423720316968
CARGO_SUBTENENTE_ID = 1500866187872043048
CARGO_ASPIRANTE_ID = 1500872729643974656
CARGO_TENENTE_ID = 1500866376804466892
CARGO_CORONEL_ID = 1497929159286980699
CARGO_TENENTE_CORONEL_ID = 1500832144581464125
CARGO_MAJOR_ID = 1497928998049681419
CARGO_SEM_WL_ID = 1497668807223934976

CARGO_STAFF_ID = 1500833927613386752

PONTOS_POR_ACAO = 25
PONTOS_POR_PRISAO = 30
PONTOS_POR_MULTAS = 12
PONTOS_POR_15MIN = 10

# Critérios de promoção automática
# Formato: cargo atual -> próximo cargo
CRITERIOS_PROMOCAO = [
    {
        "atual": "ALUNO",
        "atual_id": CARGO_ALUNO_ID,
        "proximo": "SOLDADO",
        "proximo_id": CARGO_SOLDADO_ID,
        "pontos": 100,
        "dias": 3,
        "relatorios": 5,
    },
    {
        "atual": "SOLDADO",
        "atual_id": CARGO_SOLDADO_ID,
        "proximo": "CABO",
        "proximo_id": CARGO_CABO_ID,
        "pontos": 400,
        "dias": 5,
        "relatorios": 10,
    },
    {
        "atual": "CABO",
        "atual_id": CARGO_CABO_ID,
        "proximo": "SARGENTO",
        "proximo_id": CARGO_SARGENTO_ID,
        "pontos": 900,
        "dias": 7,
        "relatorios": 15,
    },
    {
        "atual": "SARGENTO",
        "atual_id": CARGO_SARGENTO_ID,
        "proximo": "SUBTENENTE",
        "proximo_id": CARGO_SUBTENENTE_ID,
        "pontos": 1600,
        "dias": 10,
        "relatorios": 25,
    },
    {
        "atual": "SUBTENENTE",
        "atual_id": CARGO_SUBTENENTE_ID,
        "proximo": "ASPIRANTE A OFICIAL",
        "proximo_id": CARGO_ASPIRANTE_ID,
        "pontos": 2500,
        "dias": 14,
        "relatorios": 40,
    },
    {
        "atual": "ASPIRANTE A OFICIAL",
        "atual_id": CARGO_ASPIRANTE_ID,
        "proximo": "TENENTE",
        "proximo_id": CARGO_TENENTE_ID,
        "pontos": 3500,
        "dias": 20,
        "relatorios": 60,
    },
]


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ARQUIVO = "ponto.json"
ARQUIVO_REGISTROS = "registros.json"

pontos_ativos = {}
pontuacao = {}
registros = {}
painel_mensagem_id = None
ranking_mensagem_id = None

# =========================
# 📂 DADOS
# =========================
def carregar_dados():
    global pontuacao, registros

    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r") as f:
            pontuacao = json.load(f)

    if os.path.exists(ARQUIVO_REGISTROS):
        with open(ARQUIVO_REGISTROS, "r") as f:
            registros = json.load(f)

def salvar_dados():
    with open(ARQUIVO, "w") as f:
        json.dump(pontuacao, f, indent=4)

    with open(ARQUIVO_REGISTROS, "w") as f:
        json.dump(registros, f, indent=4)

def garantir_registro(user_id):
    user_id = str(user_id)

    if user_id not in registros:
        registros[user_id] = {
            "acoes": 0,
            "multas": 0,
            "prisoes": 0,
        }

    return registros[user_id]

def adicionar_relatorio(user_id, tipo):
    dados = garantir_registro(user_id)

    if tipo not in dados:
        dados[tipo] = 0

    dados[tipo] += 1
    salvar_dados()

def total_relatorios(user_id):
    dados = garantir_registro(user_id)
    return dados.get("acoes", 0) + dados.get("multas", 0) + dados.get("prisoes", 0)

# =========================
# 🎨 EMBED BATE PONTO
# =========================
async def gerar_embed():
    embed = discord.Embed(
        title="🚓 CENTRO DE COMANDO OPERACIONAL",
        description="📁 **DEPARTAMENTO DE OPERAÇÕES | POLÍCIA MILITAR**\n\n"
                    "🧾 **Painel de Controle de Ponto**\n"
                    "Utilize os botões abaixo para gerenciar seu turno.\n\n"
                    "⚡ **Compromisso com a Excelência**\n"
                    "*Para que o mal não prevaleça, a justiça nunca descansa.*",
        color=discord.Color.dark_blue()
    )

    embed.add_field(
        name="📊 ESTATÍSTICAS DO SISTEMA",
        value=f"⬛ Bonificação: {PONTOS_POR_15MIN} Pontos / 15 Minutos\n⬛ Status: Sistema Operacional",
        inline=False
    )

    if not pontos_ativos:
        ativos_txt = "⬛ Nenhum oficial ativo no momento"
    else:
        ativos_txt = ""
        for user_id, inicio in pontos_ativos.items():
            user = await bot.fetch_user(user_id)
            tempo = datetime.now() - inicio
            minutos = int(tempo.total_seconds() // 60)
            pontos = (minutos // 15) * PONTOS_POR_15MIN
            ativos_txt += f"⬛ {user.name} | {minutos} min | {pontos} pts\n"

    embed.add_field(name="👮 OFICIAIS EM SERVIÇO", value=ativos_txt, inline=False)
    embed.set_footer(text="Sistema Integrado de Gestão • Polícia Militar")

    return embed


# =========================
# 🏆 RANKING DE PONTOS
# =========================
def obter_patente_membro(member):
    if not member:
        return "Não encontrado"

    ordem_patentes = [
        (CARGO_TENENTE_ID, "TENENTE"),
        (CARGO_ASPIRANTE_ID, "ASPIRANTE A OFICIAL"),
        (CARGO_SUBTENENTE_ID, "SUBTENENTE"),
        (CARGO_SARGENTO_ID, "SARGENTO"),
        (CARGO_CABO_ID, "CABO"),
        (CARGO_SOLDADO_ID, "SOLDADO"),
        (CARGO_ALUNO_ID, "ALUNO"),
    ]

    cargos_usuario = {role.id for role in member.roles}

    for cargo_id, nome in ordem_patentes:
        if cargo_id in cargos_usuario:
            return nome

    return "Sem patente"

async def gerar_embed_ranking(guild):
    embed = discord.Embed(
        title="🏆 RANKING DE PONTOS",
        description="Ranking geral dos oficiais do servidor.",
        color=discord.Color.gold()
    )

    membros = []

    # Tenta carregar todos os membros do servidor.
    # Para funcionar 100%, ative Server Members Intent no Developer Portal.
    try:
        await asyncio.wait_for(guild.chunk(), timeout=8)
    except Exception as e:
        print(f"⚠️ Não consegui carregar todos os membros para o ranking: {e}")

    # Se o cache de membros carregou, mostra todos os membros do servidor
    if guild.members:
        for member in guild.members:
            if member.bot:
                continue

            user_id = str(member.id)
            pontos = pontuacao.get(user_id, 0)

            if isinstance(pontos, dict):
                pontos = pontos.get("pontos", 0)

            membros.append({
                "member": member,
                "nome": member.display_name,
                "pontos": pontos,
                "patente": obter_patente_membro(member)
            })

    # Fallback: se não conseguiu carregar membros, mostra quem existe no ponto.json
    if not membros:
        print("⚠️ Ranking usando fallback do ponto.json. Ative Server Members Intent para listar todos.")
        for user_id, pontos in pontuacao.items():
            if isinstance(pontos, dict):
                pontos = pontos.get("pontos", 0)

            member = guild.get_member(int(user_id))

            if member:
                nome = member.display_name
                patente = obter_patente_membro(member)
            else:
                nome = f"Usuário {user_id}"
                patente = "Não encontrado"

            membros.append({
                "member": member,
                "nome": nome,
                "pontos": pontos,
                "patente": patente
            })

    membros = sorted(membros, key=lambda x: x["pontos"], reverse=True)

    if not membros:
        embed.add_field(name="📊 Oficiais", value="Nenhum membro encontrado.", inline=False)
        embed.set_footer(text="Ranking atualizado automaticamente")
        return embed

    texto = ""

    for posicao, dados in enumerate(membros[:30], start=1):
        texto += f"**{posicao}º** | **{dados['patente']}** | {dados['nome']} | **{dados['pontos']} pts**\n"

    embed.add_field(name="📊 Oficiais", value=texto, inline=False)
    embed.set_footer(text="Ranking atualizado automaticamente")

    return embed

async def atualizar_ranking():
    global ranking_mensagem_id

    if ranking_mensagem_id is None:
        return

    canal = bot.get_channel(CANAL_RANKING)
    if canal is None:
        return

    try:
        mensagem = await canal.fetch_message(ranking_mensagem_id)
    except:
        return

    embed = await gerar_embed_ranking(canal.guild)
    await mensagem.edit(embed=embed)

# =========================
# 🔄 ATUALIZAR PAINEL
# =========================
async def atualizar_painel():
    global painel_mensagem_id

    if painel_mensagem_id is None:
        return

    canal = bot.get_channel(CANAL_BATE_PONTO)
    if canal is None:
        return

    try:
        mensagem = await canal.fetch_message(painel_mensagem_id)
    except:
        return

    embed = await gerar_embed()
    await mensagem.edit(embed=embed, view=PainelPonto())

# =========================
# ⏱️ LOOP
# =========================
@tasks.loop(seconds=30)
async def loop_painel():
    await atualizar_painel()
    await atualizar_ranking()

# =========================
# 🎛️ BOTÕES BATE PONTO
# =========================
class PainelPonto(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Iniciar Turno", style=discord.ButtonStyle.green)
    async def iniciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        if user.id in pontos_ativos:
            await interaction.response.send_message("Você já está em turno!", ephemeral=True)
            return

        pontos_ativos[user.id] = datetime.now()
        await interaction.response.send_message("✅ Turno iniciado!", ephemeral=True)

        await atualizar_painel()

    @discord.ui.button(label="🔴 Encerrar Turno", style=discord.ButtonStyle.red)
    async def encerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        if user.id not in pontos_ativos:
            await interaction.response.send_message("Você não iniciou turno!", ephemeral=True)
            return

        inicio = pontos_ativos.pop(user.id)
        minutos = int((datetime.now() - inicio).total_seconds() // 60)
        pontos = (minutos // 15) * PONTOS_POR_15MIN

        user_id = str(user.id)
        pontuacao[user_id] = pontuacao.get(user_id, 0) + pontos
        salvar_dados()

        await interaction.response.send_message(
            f"⏹️ Turno encerrado!\nTempo: {minutos} min\nPontos: {pontos}",
            ephemeral=True
        )

        await atualizar_painel()
# =========================
#BOTÃO MULTAS
# =========================
class BotoesMulta(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    def is_staff(self, interaction):
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True

        if not interaction.guild:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False

        return any(role.id == CARGO_STAFF_ID for role in member.roles)

    @discord.ui.button(label="✅ Aprovar Multa", style=discord.ButtonStyle.green)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        user_id = str(self.user_id)
        pontuacao[user_id] = pontuacao.get(user_id, 0) + PONTOS_POR_MULTAS
        adicionar_relatorio(user_id, "multas")
        salvar_dados()

        embed.color = discord.Color.green()
        embed.add_field(name="Status", value=f"Aprovado por {interaction.user.mention}", inline=False)
        embed.add_field(name="Pontos", value=f"+{PONTOS_POR_MULTAS} pts", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Multa aprovada!", ephemeral=True)

        try:
            user = await bot.fetch_user(self.user_id)
            await user.send(f"💰 Sua multa foi aprovada!\nVocê recebeu +{PONTOS_POR_MULTAS} pontos.")
        except:
            pass

        canal_log = bot.get_channel(CANAL_LOG_MULTAS)

        if canal_log:
            log_embed = discord.Embed(
                title="💰 Multa Aprovada",
                color=discord.Color.green()
            )

            for field in embed.fields:
                log_embed.add_field(name=field.name, value=field.value, inline=False)

            if embed.image:
                log_embed.set_image(url=embed.image.url)

            if embed.footer:
                log_embed.set_footer(text=embed.footer.text)

            await canal_log.send(embed=log_embed)

    @discord.ui.button(label="❌ Recusar Multa", style=discord.ButtonStyle.red)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"Recusado por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Multa recusada!", ephemeral=True)

# =========================
# ⚠️ PERMISSÃO ADVERTÊNCIA
# =========================
def pode_registrar_advertencia(member):
    if not member:
        return False

    cargos = {role.id for role in member.roles}

    return (
        CARGO_CORONEL_ID in cargos
        or CARGO_TENENTE_CORONEL_ID in cargos
        or CARGO_MAJOR_ID in cargos
    )


# =========================
# ⚠️ MODAL ADVERTÊNCIA
# =========================
class ModalAdvertencia(discord.ui.Modal, title="Registrar Advertência"):

    jogador_id = discord.ui.TextInput(
        label="ID do jogador advertido",
        required=True
    )

    nome = discord.ui.TextInput(
        label="Nome do jogador advertido",
        required=True
    )

    motivo = discord.ui.TextInput(
        label="Motivo da advertência",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:
            jogador = await interaction.guild.fetch_member(int(self.jogador_id.value))
            mencao_jogador = jogador.mention
        except:
            jogador = None
            mencao_jogador = f"`{self.jogador_id.value}`"

        embed = discord.Embed(
            title="⚠️ ADVERTÊNCIA REGISTRADA",
            color=discord.Color.orange()
        )

        embed.add_field(name="👤 Jogador advertido", value=mencao_jogador, inline=False)
        embed.add_field(name="📛 Nome informado", value=self.nome.value, inline=False)
        embed.add_field(name="🆔 ID", value=self.jogador_id.value, inline=False)
        embed.add_field(name="📝 Motivo", value=self.motivo.value, inline=False)
        embed.add_field(name="👮 Registrado por", value=interaction.user.mention, inline=False)
        embed.set_footer(text=f"Registrado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        canal = bot.get_channel(CANAL_ADVERTENCIAS)

        if not canal:
            await interaction.response.send_message(
                "Canal de advertências não encontrado. Confira o ID do canal CANAL_ADVERTENCIAS.",
                ephemeral=True
            )
            return

        await canal.send(
            content=f"⚠️ Advertência registrada para {mencao_jogador}",
            embed=embed
        )

        try:
            if jogador:
                await jogador.send(
                    f"⚠️ Você recebeu uma advertência.\n\n"
                    f"Motivo: {self.motivo.value}\n"
                    f"Registrado por: {interaction.user.display_name}"
                )
        except:
            pass

        await interaction.response.send_message(
            "Advertência registrada com sucesso!",
            ephemeral=True
        )

# =========================
# 📝 MODAL WL
# =========================
class ModalWL(discord.ui.Modal, title="Registro de WL"):

    nome = discord.ui.TextInput(
        label="Seu nome",
        required=True,
        max_length=50
    )

    id_jogador = discord.ui.TextInput(
        label="Seu ID",
        required=True,
        max_length=20
    )

    recrutador = discord.ui.TextInput(
        label="Quem recrutou você?",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        novo_nome = f"{self.nome.value} | {self.id_jogador.value}"

        # Tenta mudar o apelido do usuário no servidor
        try:
            await interaction.user.edit(nick=novo_nome)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Não consegui alterar seu nome no servidor. Coloque o cargo do bot acima do cargo do membro.",
                ephemeral=True
            )
            return
        except Exception as e:
            print(f"⚠️ Erro ao alterar nick na WL: {e}")

        embed = discord.Embed(
            title="📝 NOVA WL PARA ANÁLISE",
            color=discord.Color.blue()
        )

        embed.add_field(name="👤 Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="📛 Nome", value=self.nome.value, inline=False)
        embed.add_field(name="🆔 ID", value=self.id_jogador.value, inline=False)
        embed.add_field(name="🤝 Recrutado por", value=self.recrutador.value, inline=False)
        embed.add_field(name="🪪 Nome no servidor", value=novo_nome, inline=False)
        embed.set_footer(text=f"Enviado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        canal = bot.get_channel(CANAL_LOGS_WL)

        if not canal:
            await interaction.response.send_message(
                "Canal de logs WL não encontrado. Confira o ID CANAL_LOGS_WL.",
                ephemeral=True
            )
            return

        await canal.send(embed=embed, view=BotoesWL(interaction.user.id))

        await interaction.response.send_message(
            "✅ Sua WL foi enviada para análise! Aguarde aprovação.",
            ephemeral=True
        )

# =========================
# ✅ BOTÕES WL
# =========================
class BotoesWL(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    def is_staff(self, interaction):
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True

        if not interaction.guild:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False

        return any(role.id == CARGO_STAFF_ID for role in member.roles)

    @discord.ui.button(label="✅ Aprovar WL", style=discord.ButtonStyle.green)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Essa WL já foi analisada.", ephemeral=True)
            return

        member = interaction.guild.get_member(self.user_id)
        if not member:
            try:
                member = await interaction.guild.fetch_member(self.user_id)
            except:
                await interaction.response.send_message("Não consegui encontrar o membro.", ephemeral=True)
                return

        cargo_sem_wl = interaction.guild.get_role(CARGO_SEM_WL_ID)
        cargo_aluno = interaction.guild.get_role(CARGO_ALUNO_ID)

        if not cargo_aluno:
            await interaction.response.send_message("Cargo ALUNO não encontrado. Confira o ID.", ephemeral=True)
            return

        try:
            if cargo_sem_wl and cargo_sem_wl in member.roles:
                await member.remove_roles(cargo_sem_wl)

            await member.add_roles(cargo_aluno)

        except discord.Forbidden:
            await interaction.response.send_message(
                "Não tenho permissão para alterar cargos. Coloque o cargo do bot acima de SEM WL e ALUNO.",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.response.send_message(f"Erro ao alterar cargos: {e}", ephemeral=True)
            return

        embed.color = discord.Color.green()
        embed.add_field(name="Status", value=f"✅ WL aprovada por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("WL aprovada!", ephemeral=True)

        try:
            await member.send(
                "✅ Sua WL foi aprovada!\n\n"
                "Você recebeu o cargo de **ALUNO**. Seja bem-vindo!"
            )
        except:
            pass

    @discord.ui.button(label="❌ Recusar WL", style=discord.ButtonStyle.red)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Essa WL já foi analisada.", ephemeral=True)
            return

        member = interaction.guild.get_member(self.user_id)
        if not member:
            try:
                member = await interaction.guild.fetch_member(self.user_id)
            except:
                member = None

        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"❌ WL recusada por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("WL recusada!", ephemeral=True)

        try:
            if member:
                await member.send(
                    "❌ Sua WL foi recusada.\n\n"
                    "Procure um responsável para mais informações."
                )
        except:
            pass

# =========================
# 📄 MODAL AUSÊNCIA
# =========================
class ModalAusencia(discord.ui.Modal, title="Solicitação de Ausência"):

    motivo = discord.ui.TextInput(
        label="Motivo da ausência",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📄 Solicitação de Ausência", color=discord.Color.orange())
        embed.add_field(name="👤 Oficial", value=interaction.user.mention, inline=False)
        embed.add_field(name="📝 Motivo", value=self.motivo.value, inline=False)
        embed.set_footer(text=f"Solicitado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        canal = bot.get_channel(CANAL_ANALISE)
        view = BotoesAprovacao()

        await canal.send(embed=embed, view=view)
        await interaction.response.send_message("Solicitação enviada para análise!", ephemeral=True)

# =========================
# 📋 MODAL AÇÃO
# =========================
class ModalAcao(discord.ui.Modal, title="Registro de Ação"):

    descricao = discord.ui.TextInput(
        label="Descreva a ação realizada",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📋 Nova Ação Registrada",
            color=discord.Color.blue()
        )

        embed.add_field(name="👤 Oficial", value=interaction.user.mention, inline=False)
        embed.add_field(name="📝 Ação", value=self.descricao.value, inline=False)
        embed.set_footer(text=f"Enviado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        canal = bot.get_channel(CANAL_PAINEL_ACOES)
        view = BotoesAcao(interaction.user.id)

        await canal.send(embed=embed, view=view)
        await interaction.response.send_message("Ação enviada para aprovação!", ephemeral=True)

# =========================
# 🚔 MODAL PRISÃO
# =========================
class ModalPrisao(discord.ui.Modal, title="Registro de Prisão"):

    descricao = discord.ui.TextInput(
        label="Descreva a prisão",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.send_message(
            "📷 Agora envie a imagem da prisão aqui no chat.",
            ephemeral=True
        )

        def check(msg):
            return msg.author == interaction.user and msg.attachments

        try:
            msg = await bot.wait_for("message", timeout=60, check=check)
        except:
            await interaction.followup.send("Tempo esgotado para enviar imagem.", ephemeral=True)
            return

        imagem = msg.attachments[0].url

        embed = discord.Embed(
            title="🚔 Nova Prisão Registrada",
            color=discord.Color.dark_gold()
        )

        embed.add_field(name="👤 Oficial", value=interaction.user.mention, inline=False)
        embed.add_field(name="📝 Descrição", value=self.descricao.value, inline=False)
        embed.set_image(url=imagem)
        embed.set_footer(text=f"Enviado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        canal = bot.get_channel(CANAL_PAINEL_PRISAO)
        view = BotoesPrisao(interaction.user.id)

        await canal.send(embed=embed, view=view)
        await interaction.followup.send("Prisão enviada para aprovação!", ephemeral=True)

#==========================
#MODAL MULTAS
#==========================
class ModalMulta(discord.ui.Modal, title="Registro de Multa"):

    descricao = discord.ui.TextInput(
        label="Descreva a multa",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.send_message(
            "📷 Agora envie a imagem da multa aqui no chat.",
            ephemeral=True
        )

        def check(msg):
            return msg.author == interaction.user and msg.attachments

        try:
            msg = await bot.wait_for("message", timeout=60, check=check)
        except:
            await interaction.followup.send("Tempo esgotado para enviar imagem.", ephemeral=True)
            return

        imagem = msg.attachments[0].url

        embed = discord.Embed(
            title="💰 Nova Multa Registrada",
            color=discord.Color.orange()
        )

        embed.add_field(name="👤 Oficial", value=interaction.user.mention, inline=False)
        embed.add_field(name="📝 Descrição", value=self.descricao.value, inline=False)
        embed.set_image(url=imagem)
        embed.set_footer(text=f"Enviado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        canal = bot.get_channel(CANAL_PAINEL_MULTAS)
        view = BotoesMulta(interaction.user.id)

        await canal.send(embed=embed, view=view)
        await interaction.followup.send("Multa enviada para aprovação!", ephemeral=True)

# =========================
# ✅ APROVAÇÃO AUSÊNCIA
# =========================
class BotoesAprovacao(View):
    def __init__(self):
        super().__init__(timeout=None)

    def is_staff(self, interaction):
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True

        if not interaction.guild:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False

        return any(role.id == CARGO_STAFF_ID for role in member.roles)

    @discord.ui.button(label="✅ Aprovar", style=discord.ButtonStyle.green)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        embed.color = discord.Color.green()
        embed.add_field(name="Status", value=f"Aprovado por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Aprovado!", ephemeral=True)

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.red)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"Recusado por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Recusado!", ephemeral=True)

# =========================
# ✅ APROVAÇÃO AÇÕES
# =========================
class BotoesAcao(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    def is_staff(self, interaction):
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True

        if not interaction.guild:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False

        return any(role.id == CARGO_STAFF_ID for role in member.roles)

    @discord.ui.button(label="✅ Aprovar Ação", style=discord.ButtonStyle.green)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        user_id = str(self.user_id)
        pontuacao[user_id] = pontuacao.get(user_id, 0) + PONTOS_POR_ACAO
        adicionar_relatorio(user_id, "acoes")
        salvar_dados()

        embed.color = discord.Color.green()
        embed.add_field(name="Status", value=f"Aprovado por {interaction.user.mention}", inline=False)
        embed.add_field(name="Pontos", value=f"+{PONTOS_POR_ACAO} pts", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Ação aprovada!", ephemeral=True)

        try:
            user = await bot.fetch_user(self.user_id)
            await user.send(f"✅ Sua ação foi aprovada!\nVocê recebeu +{PONTOS_POR_ACAO} pontos.")
        except:
            pass

        canal_log = bot.get_channel(CANAL_LOG_ACOES)

        if canal_log:
            log_embed = discord.Embed(
                title="📋 Ação Aprovada",
                color=discord.Color.green()
            )

            for field in embed.fields:
                log_embed.add_field(name=field.name, value=field.value, inline=False)

            if embed.footer:
                log_embed.set_footer(text=embed.footer.text)

            await canal_log.send(embed=log_embed)

    @discord.ui.button(label="❌ Recusar Ação", style=discord.ButtonStyle.red)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"Recusado por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Ação recusada!", ephemeral=True)

# =========================
# ✅ APROVAÇÃO PRISÃO
# =========================
class BotoesPrisao(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    def is_staff(self, interaction):
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True

        if not interaction.guild:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False

        return any(role.id == CARGO_STAFF_ID for role in member.roles)

    @discord.ui.button(label="✅ Aprovar Prisão", style=discord.ButtonStyle.green)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        user_id = str(self.user_id)
        pontuacao[user_id] = pontuacao.get(user_id, 0) + PONTOS_POR_PRISAO
        adicionar_relatorio(user_id, "prisoes")
        salvar_dados()

        embed.color = discord.Color.green()
        embed.add_field(name="Status", value=f"Aprovado por {interaction.user.mention}", inline=False)
        embed.add_field(name="Pontos", value=f"+{PONTOS_POR_PRISAO} pts", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Prisão aprovada!", ephemeral=True)

        try:
            user = await bot.fetch_user(self.user_id)
            await user.send(f"🚔 Sua prisão foi aprovada!\nVocê recebeu +{PONTOS_POR_PRISAO} pontos.")
        except:
            pass

        canal_log = bot.get_channel(CANAL_LOG_PRISAO)

        if canal_log:
            log_embed = discord.Embed(
                title="🚔 Prisão Aprovada",
                color=discord.Color.green()
            )

            for field in embed.fields:
                log_embed.add_field(name=field.name, value=field.value, inline=False)

            if embed.image:
                log_embed.set_image(url=embed.image.url)

            if embed.footer:
                log_embed.set_footer(text=embed.footer.text)

            await canal_log.send(embed=log_embed)

    @discord.ui.button(label="❌ Recusar Prisão", style=discord.ButtonStyle.red)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"Recusado por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Prisão recusada!", ephemeral=True)


# =========================
# 🎖️ SISTEMA DE PROMOÇÃO
# =========================
def obter_criterio_promocao(member):
    cargos_usuario = {role.id for role in member.roles}

    for criterio in CRITERIOS_PROMOCAO:
        if criterio["atual_id"] in cargos_usuario:
            return criterio

    return None

def dias_no_servidor(member):
    if not member.joined_at:
        return 0

    agora = datetime.now(member.joined_at.tzinfo)
    return (agora - member.joined_at).days

def montar_status_promocao(member, criterio):
    user_id = str(member.id)
    pontos = pontuacao.get(user_id, 0)
    relatorios = total_relatorios(user_id)
    dias = dias_no_servidor(member)

    falta = []

    if pontos < criterio["pontos"]:
        falta.append(f"❌ Pontos: {pontos}/{criterio['pontos']}")
    else:
        falta.append(f"✅ Pontos: {pontos}/{criterio['pontos']}")

    if dias < criterio["dias"]:
        falta.append(f"❌ Dias na polícia: {dias}/{criterio['dias']}")
    else:
        falta.append(f"✅ Dias na polícia: {dias}/{criterio['dias']}")

    if relatorios < criterio["relatorios"]:
        falta.append(f"❌ Relatórios: {relatorios}/{criterio['relatorios']}")
    else:
        falta.append(f"✅ Relatórios: {relatorios}/{criterio['relatorios']}")

    aprovado = (
        pontos >= criterio["pontos"]
        and dias >= criterio["dias"]
        and relatorios >= criterio["relatorios"]
    )

    return aprovado, pontos, relatorios, dias, "\n".join(falta)

class BotoesPromocao(View):
    def __init__(self, user_id, cargo_atual_id, cargo_novo_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.cargo_atual_id = cargo_atual_id
        self.cargo_novo_id = cargo_novo_id

    def is_staff(self, interaction):
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True

        if not interaction.guild:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False

        return any(role.id == CARGO_STAFF_ID for role in member.roles)

    @discord.ui.button(label="✅ Aprovar Promoção", style=discord.ButtonStyle.green)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        member = interaction.guild.get_member(self.user_id)
        if not member:
            try:
                member = await interaction.guild.fetch_member(self.user_id)
            except:
                await interaction.response.send_message("Não consegui encontrar o membro.", ephemeral=True)
                return

        cargo_atual = interaction.guild.get_role(self.cargo_atual_id)
        cargo_novo = interaction.guild.get_role(self.cargo_novo_id)

        if not cargo_atual or not cargo_novo:
            await interaction.response.send_message("Cargo atual ou novo cargo não encontrado. Confira os IDs.", ephemeral=True)
            return

        try:
            await member.remove_roles(cargo_atual)
            await member.add_roles(cargo_novo)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Não tenho permissão para alterar esses cargos. Coloque o cargo do bot acima das patentes.",
                ephemeral=True
            )
            return

        embed.color = discord.Color.green()
        embed.add_field(name="Status", value=f"✅ Promoção aprovada por {interaction.user.mention}", inline=False)
        embed.add_field(name="Resultado", value=f"{member.mention} promovido para **{cargo_novo.name}**", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Promoção aprovada!", ephemeral=True)

        try:
            await member.send(
                f"🎖️ Parabéns! Sua promoção foi aprovada!\n"
                f"Você foi promovido para **{cargo_novo.name}**."
            )
        except:
            pass

        canal_promocao_log = bot.get_channel(CANAL_NOTIFICAR_PROMOCAO)

        if canal_promocao_log:
            embed_log = discord.Embed(
                title="🎖️ PROMOÇÃO APROVADA",
                description=f"{member.mention} foi promovido para **{cargo_novo.name}**!",
                color=discord.Color.gold()
            )

            embed_log.add_field(
                name="✅ Aprovado por",
                value=interaction.user.mention,
                inline=False
            )

            embed_log.set_footer(
                text=f"Promoção registrada em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )

            await canal_promocao_log.send(embed=embed_log)

    @discord.ui.button(label="❌ Recusar Promoção", style=discord.ButtonStyle.red)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.message.embeds:
            return

        if not self.is_staff(interaction):
            await interaction.response.send_message("Sem permissão.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        if any(field.name == "Status" for field in embed.fields):
            await interaction.response.send_message("Já foi analisado.", ephemeral=True)
            return

        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"❌ Promoção recusada por {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Promoção recusada.", ephemeral=True)

class PainelPromocao(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎖️ Solicitar Promoção", style=discord.ButtonStyle.blurple)
    async def solicitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user

        if not interaction.guild:
            await interaction.response.send_message("Esse comando só funciona dentro do servidor.", ephemeral=True)
            return

        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(interaction.user.id)

        criterio = obter_criterio_promocao(member)

        if not criterio:
            await interaction.response.send_message(
                "Não encontrei uma patente elegível para promoção. Confira se os IDs dos cargos estão configurados.",
                ephemeral=True
            )
            return

        if criterio["atual_id"] == 0 or criterio["proximo_id"] == 0:
            await interaction.response.send_message(
                "Os IDs dos cargos de promoção ainda não foram configurados no código.",
                ephemeral=True
            )
            return

        aprovado, pontos, relatorios, dias, status_requisitos = montar_status_promocao(member, criterio)

        if not aprovado:
            await interaction.response.send_message(
                f"Você ainda não cumpre os requisitos para **{criterio['proximo']}**:\n\n{status_requisitos}",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎖️ Solicitação de Promoção",
            color=discord.Color.gold()
        )
        embed.add_field(name="👤 Oficial", value=member.mention, inline=False)
        embed.add_field(name="📌 Promoção", value=f"{criterio['atual']} → {criterio['proximo']}", inline=False)
        embed.add_field(name="✅ Requisitos", value=status_requisitos, inline=False)
        embed.set_footer(text=f"Solicitado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        canal = bot.get_channel(CANAL_ANALISE_PROMOCAO)
        if not canal:
            canal = bot.get_channel(CANAL_PROMOCAO)

        if not canal:
            await interaction.response.send_message("Canal de análise de promoção não configurado.", ephemeral=True)
            return

        await canal.send(
            embed=embed,
            view=BotoesPromocao(member.id, criterio["atual_id"], criterio["proximo_id"])
        )
        await interaction.response.send_message("Solicitação de promoção enviada para análise!", ephemeral=True)

# =========================
# 🎛️ PAINEL WL
# =========================
class PainelWL(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Fazer WL", style=discord.ButtonStyle.blurple)
    async def fazer_wl(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalWL())

# =========================
# 🎛️ PAINEL ADVERTÊNCIA
# =========================
class PainelAdvertencia(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚠️ Registrar Advertência", style=discord.ButtonStyle.red)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):

        member = interaction.guild.get_member(interaction.user.id)

        if not pode_registrar_advertencia(member):
            await interaction.response.send_message(
                "Você não tem permissão para registrar advertências.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(ModalAdvertencia())

# =========================
# 🎛️ PAINEL AUSÊNCIA
# =========================
class PainelAusencia(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📄 Solicitar Ausência", style=discord.ButtonStyle.blurple)
    async def solicitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalAusencia())

# =========================
# 🎛️ PAINEL AÇÕES
# =========================
class PainelAcoes(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Registrar Ação", style=discord.ButtonStyle.blurple)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalAcao())

# =========================
# 🎛️ PAINEL PRISÃO
# =========================
class PainelPrisao(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🚔 Registrar Prisão", style=discord.ButtonStyle.blurple)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalPrisao())

# ========================
# PAINEL MULTAS
# ========================
class PainelMultas(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 Registrar Multa", style=discord.ButtonStyle.blurple)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalMulta())

# =========================
# 📊 COMANDOS
# =========================
@bot.command()
async def wl(ctx):
    if ctx.channel.id != CANAL_REGISTRO_WL:
        return

    embed = discord.Embed(
        title="📝 SISTEMA DE WL",
        description="Clique abaixo para preencher sua WL.",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=PainelWL())

@bot.command()
async def advertencia(ctx):
    if ctx.channel.id != CANAL_REGISTRAR_ADVERTENCIA:
        return

    embed = discord.Embed(
        title="⚠️ SISTEMA DE ADVERTÊNCIA",
        description="Clique abaixo para registrar uma advertência.",
        color=discord.Color.orange()
    )

    await ctx.send(embed=embed, view=PainelAdvertencia())

@bot.command()
async def painel(ctx):
    global painel_mensagem_id

    if ctx.channel.id != CANAL_BATE_PONTO:
        return

    msg = await ctx.send(embed=await gerar_embed(), view=PainelPonto())
    painel_mensagem_id = msg.id

@bot.command()
async def ausencia(ctx):
    if ctx.channel.id != CANAL_AUSENCIA:
        return

    embed = discord.Embed(
        title="📄 SISTEMA DE AUSÊNCIA",
        description="Clique abaixo para solicitar ausência.",
        color=discord.Color.orange()
    )

    await ctx.send(embed=embed, view=PainelAusencia())

@bot.command()
async def acoes(ctx):
    embed = discord.Embed(
        title="📋 SISTEMA DE AÇÕES",
        description="Clique abaixo para registrar uma ação.",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=PainelAcoes())

@bot.command()
async def prisao(ctx):
    embed = discord.Embed(
        title="🚔 SISTEMA DE PRISÃO",
        description="Clique abaixo para registrar uma prisão.",
        color=discord.Color.gold()
    )

    await ctx.send(embed=embed, view=PainelPrisao())

@bot.command()
async def multa(ctx):
    embed = discord.Embed(
        title="💰 SISTEMA DE MULTAS",
        description="Clique abaixo para registrar uma multa.",
        color=discord.Color.orange()
    )

    await ctx.send(embed=embed, view=PainelMultas())



@bot.command()
async def ranking(ctx):
    global ranking_mensagem_id

    if CANAL_RANKING and ctx.channel.id != CANAL_RANKING:
        return

    embed = await gerar_embed_ranking(ctx.guild)
    msg = await ctx.send(embed=embed)
    ranking_mensagem_id = msg.id

@bot.command()
async def promocao(ctx):
    if CANAL_PROMOCAO and ctx.channel.id != CANAL_PROMOCAO:
        return

    embed = discord.Embed(
        title="🎖️ SISTEMA DE PROMOÇÃO",
        description="Clique abaixo para solicitar sua promoção. O bot verificará pontos, dias e relatórios automaticamente.",
        color=discord.Color.gold()
    )

    await ctx.send(embed=embed, view=PainelPromocao())

# =========================
# 👤 ENTRADA NO SERVIDOR / SEM WL
# =========================
@bot.event
async def on_member_join(member):
    cargo_sem_wl = member.guild.get_role(CARGO_SEM_WL_ID)

    if not cargo_sem_wl:
        print("❌ Cargo SEM WL não encontrado. Confira o ID CARGO_SEM_WL_ID.")
        return

    try:
        await member.add_roles(cargo_sem_wl)
        print(f"✅ Cargo SEM WL dado para {member.name}")
    except discord.Forbidden:
        print("❌ Sem permissão para dar o cargo SEM WL. Coloque o cargo do bot acima dele.")
    except Exception as e:
        print(f"❌ Erro ao dar cargo SEM WL: {e}")

# =========================
# 🚀 READY
# =========================
@bot.event
async def on_ready():
    global ranking_mensagem_id

    carregar_dados()

    if not loop_painel.is_running():
        loop_painel.start()

    print(f"Bot online como {bot.user}")

    paineis = [
        (CANAL_BATE_PONTO, "BATE PONTO", await gerar_embed(), PainelPonto()),
        (CANAL_AUSENCIA, "AUSÊNCIA", discord.Embed(title="📄 SISTEMA DE AUSÊNCIA", description="Clique abaixo para solicitar ausência.", color=discord.Color.orange()), PainelAusencia()),
        (
            CANAL_REGISTRO_WL,
            "WL",
            discord.Embed(
                title="📝 SISTEMA DE WL",
                description="Clique abaixo para preencher sua WL.",
                color=discord.Color.blue()
            ),
            PainelWL()
        ),
        (CANAL_LOG_ACOES, "AÇÕES", discord.Embed(title="📋 SISTEMA DE AÇÕES", description="Clique abaixo para registrar uma ação.", color=discord.Color.blue()), PainelAcoes()),
        (
            CANAL_REGISTRAR_ADVERTENCIA,
            "ADVERTÊNCIA",
            discord.Embed(
                title="⚠️ SISTEMA DE ADVERTÊNCIA",
                description="Clique abaixo para registrar uma advertência.",
                color=discord.Color.orange()
            ),
            PainelAdvertencia()
        ),
        (CANAL_LOG_PRISAO, "PRISÃO", discord.Embed(title="🚔 SISTEMA DE PRISÃO", description="Clique abaixo para registrar uma prisão.", color=discord.Color.gold()), PainelPrisao()),
        (CANAL_LOG_MULTAS, "MULTAS", discord.Embed(title="💰 SISTEMA DE MULTAS", description="Clique abaixo para registrar uma multa.", color=discord.Color.orange()), PainelMultas()),
        (CANAL_PROMOCAO, "PROMOÇÃO", discord.Embed(title="🎖️ SISTEMA DE PROMOÇÃO", description="Clique abaixo para solicitar sua promoção.", color=discord.Color.gold()), PainelPromocao()),
    ]

    for canal_id, nome, embed, view in paineis:
        try:
            canal = bot.get_channel(canal_id)

            if canal is None:
                print(f"❌ Canal não encontrado: {nome} | ID: {canal_id}")
                continue

            async for msg in canal.history(limit=10):
                if msg.author == bot.user:
                    await msg.delete()

            await canal.send(embed=embed, view=view)
            print(f"✅ Painel criado: {nome}")

        except Exception as e:
            print(f"❌ Erro ao criar painel {nome}: {e}")

    print("🔄 Tentando criar ranking...")

    try:
        canal = await bot.fetch_channel(CANAL_RANKING)

        if canal is None:
            print(f"❌ Canal de ranking não encontrado | ID: {CANAL_RANKING}")
            return

        async for msg in canal.history(limit=10):
            if msg.author == bot.user:
                await msg.delete()

        print("🔄 Gerando embed do ranking...")
        embed = await gerar_embed_ranking(canal.guild)

        msg = await canal.send(embed=embed)
        ranking_mensagem_id = msg.id

        print("✅ Ranking criado")

    except Exception as e:
        print(f"❌ Erro ao criar ranking: {e}")

# =========================
# ▶️ START
# =========================
if not TOKEN:
    raise ValueError("TOKEN não encontrado. Configure a variável de ambiente TOKEN antes de iniciar o bot.")

bot.run(TOKEN)
