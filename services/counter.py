"""Lógica de contagem de bovinos a partir de detecções rastreadas.

Quatro métricas distintas, que NÃO são equivalentes:
  1. detectados_quadro - animais detectados no quadro atual.
  2. ids_unicos        - IDs de rastreamento distintos vistos na sessão (pode superestimar:
                         o mesmo animal pode ganhar um ID novo após oclusão ou saída do quadro).
  3. contados          - animais contados segundo a regra escolhida (cada ID conta no máximo UMA vez).
  4. estimativa_min/max- faixa estimada do total. Nunca é apresentada como valor exato.

Nunca se soma o total de detecções de todos os quadros.

Linha virtual (regra recomendada para contar animais que PASSAM, com a câmera parada):
  A linha vai do ponto A ao ponto B (frações 0..1 do quadro). A "seta" aponta para o lado
  positivo. Cruzar no sentido da seta = ENTRADA; no sentido contrário = SAÍDA.
  Uma zona de tolerância em torno da linha ignora o tremor das caixas.
"""
import math
from dataclasses import dataclass, field

ESTRATEGIAS = ("ids_estaveis", "linha_virtual", "area_interesse", "varredura_drone")
SENTIDOS = ("ambos", "entrada", "saida")


@dataclass
class ConfigContagem:
    estrategia: str = "ids_estaveis"
    min_quadros: int = 5                       # quadros mínimos para um ID ser considerado estável
    # Linha virtual / portão de varredura: (xA, yA, xB, yB) em frações do quadro.
    linha: tuple = (0.0, 0.5, 1.0, 0.5)
    sentido_contado: str = "ambos"             # "ambos", "entrada" (sentido da seta) ou "saida"
    banda_tolerancia: float = 0.01             # zona morta, fração da diagonal do quadro
    min_quadros_linha: int = 3                 # idade mínima do ID para o cruzamento valer
    area: tuple = (0.2, 0.2, 0.8, 0.8)         # (x1, y1, x2, y2) em frações do quadro
    camera_em_movimento: bool = True
    dedup_espacial: float = 0.10               # raio de deduplicação (fração da largura do quadro)
    dedup_tempo_quadros: int = 90              # janela de tempo (em quadros) para mesclar mesmo animal


@dataclass
class ResultadoContagem:
    estrategia: str
    detectados_quadro: int
    ids_unicos: int
    contados: int
    estimativa_min: int
    estimativa_max: int
    pico_simultaneo: int
    quadros_processados: int
    entradas: int = 0
    saidas: int = 0
    avisos: list[str] = field(default_factory=list)

    @property
    def saldo(self) -> int:
        return self.entradas - self.saidas

    @property
    def texto_estimativa(self) -> str:
        if self.quadros_processados == 0:
            return "—"
        if self.estimativa_min == self.estimativa_max:
            return f"≈ {self.estimativa_min}"
        return f"{self.estimativa_min} a {self.estimativa_max}"


def vetor_normal(linha: tuple, largura: int, altura: int) -> tuple[float, float]:
    """Normal unitária (em pixels) apontando para o lado positivo (sentido da seta)."""
    xa, ya, xb, yb = linha[0] * largura, linha[1] * altura, linha[2] * largura, linha[3] * altura
    dx, dy = xb - xa, yb - ya
    n = math.hypot(dx, dy) or 1.0
    return -dy / n, dx / n


class ContadorBovinos:
    def __init__(self, config: ConfigContagem | None = None):
        self.config = config or ConfigContagem()
        if self.config.estrategia not in ESTRATEGIAS:
            raise ValueError(f"Estratégia desconhecida: {self.config.estrategia}. Use {ESTRATEGIAS}.")
        if self.config.sentido_contado not in SENTIDOS:
            raise ValueError(f"Sentido desconhecido: {self.config.sentido_contado}. Use {SENTIDOS}.")
        self._quadros = 0
        self._detectados_quadro = 0
        self._pico = 0
        self._sem_id = 0
        self._vistos: dict[int, int] = {}          # id -> quadros em que apareceu
        self._lado: dict[int, int] = {}            # id -> último lado confirmado (+1 / -1)
        self._dentro: dict[int, int] = {}          # id -> quadros dentro da área
        self._contados: set[int] = set()           # regras: ids estáveis / área
        self._entradas: set[int] = set()
        self._saidas: set[int] = set()
        self._eventos_cruzamento: list[tuple[int, float, float, int, str]] = []  # (quadro, cx, cy, id, sentido)
        self._entradas_dedup = 0
        self._saidas_dedup = 0
        self._reencontros = 0

    # ---------- atualização ----------
    def atualizar(self, deteccoes, largura: int, altura: int) -> None:
        self._quadros += 1
        self._detectados_quadro = len(deteccoes)
        self._pico = max(self._pico, len(deteccoes))
        for d in deteccoes:
            if d.id_rastreamento is None:
                self._sem_id += 1
                continue
            if getattr(d, "possivel_perda", False):
                self._reencontros += 1
            i = d.id_rastreamento
            self._vistos[i] = self._vistos.get(i, 0) + 1
            cx, cy = (d.x1 + d.x2) / 2, (d.y1 + d.y2) / 2
            e = self.config.estrategia
            if e == "ids_estaveis":
                if self._vistos[i] >= self.config.min_quadros:
                    self._contados.add(i)
            elif e in ("linha_virtual", "varredura_drone"):
                self._atualizar_linha(i, cx, cy, largura, altura)
            else:
                self._atualizar_area(i, cx, cy, largura, altura)

    def _atualizar_linha(self, i, cx, cy, largura, altura):
        c = self.config
        xa, ya, xb, yb = c.linha[0] * largura, c.linha[1] * altura, c.linha[2] * largura, c.linha[3] * altura
        dx, dy = xb - xa, yb - ya
        comprimento = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / comprimento, dx / comprimento
        dist = (cx - xa) * nx + (cy - ya) * ny                   # distância com sinal até a linha
        t = ((cx - xa) * dx + (cy - ya) * dy) / (comprimento ** 2)  # posição ao longo do segmento
        banda = c.banda_tolerancia * math.hypot(largura, altura)
        if abs(dist) <= banda:
            return  # zona morta: ignora tremor da caixa junto à linha
        lado = 1 if dist > 0 else -1
        anterior = self._lado.get(i)
        self._lado[i] = lado
        if anterior is None or anterior == lado:
            return
        if not (0.0 <= t <= 1.0):
            return  # cruzou o prolongamento da linha, fora do segmento desenhado
        if self._vistos[i] < c.min_quadros_linha:
            return  # trilha muito recente: pode ser ruído de rastreamento
        sentido = "entrada" if lado > 0 else "saida"
        (self._entradas if lado > 0 else self._saidas).add(i)

        # Deduplicação espaço-temporal anti-repetição
        eh_duplicata = False
        if c.dedup_espacial > 0:
            raio_px = c.dedup_espacial * math.hypot(largura, altura)
            for q_ev, x_ev, y_ev, id_ev, sent_ev in self._eventos_cruzamento:
                if sent_ev == sentido and (self._quadros - q_ev) <= c.dedup_tempo_quadros:
                    if math.hypot(cx - x_ev, cy - y_ev) <= raio_px:
                        eh_duplicata = True
                        break

        if not eh_duplicata:
            self._eventos_cruzamento.append((self._quadros, cx, cy, i, sentido))
            if sentido == "entrada":
                self._entradas_dedup += 1
            else:
                self._saidas_dedup += 1

    def _atualizar_area(self, i, cx, cy, largura, altura):
        x1, y1, x2, y2 = self.config.area
        if x1 * largura <= cx <= x2 * largura and y1 * altura <= cy <= y2 * altura:
            self._dentro[i] = self._dentro.get(i, 0) + 1
            if self._dentro[i] >= self.config.min_quadros:
                self._contados.add(i)

    # ---------- resultado ----------
    def resultado(self) -> ResultadoContagem:
        c = self.config
        estaveis = sum(1 for n in self._vistos.values() if n >= c.min_quadros)
        avisos: list[str] = []
        entradas = len(self._entradas)
        saidas = len(self._saidas)

        if self._quadros == 0:
            avisos.append("Nenhum quadro foi processado; não há dados de contagem.")
        if c.estrategia == "ids_estaveis":
            contados = len(self._contados)
            est_max = estaveis
            est_min = min(self._pico, estaveis) if estaveis else self._pico
            avisos.append("Contagem por IDs estáveis: não garante ausência de duplicidade. "
                          "Trate o resultado como estimativa.")
            if c.camera_em_movimento:
                avisos.append("Câmera em movimento: o mesmo animal pode receber IDs diferentes ao sair e "
                              "voltar ao quadro, e animais fora do campo de visão não são contados.")
        elif c.estrategia == "varredura_drone":
            if c.sentido_contado == "entrada":
                contados = self._entradas_dedup
            elif c.sentido_contado == "saida":
                contados = self._saidas_dedup
            else:
                contados = self._entradas_dedup + self._saidas_dedup
            est_min = est_max = contados
            entradas = self._entradas_dedup
            saidas = self._saidas_dedup
            avisos.append("Varredura por Drone ativa: contagem direcional com filtro anti-repetição espaço-temporal. "
                          "Cada bovino é contado uma única vez sem repetição durante o vôo.")
        elif c.estrategia == "linha_virtual":
            if c.sentido_contado == "entrada":
                contados = len(self._entradas)
            elif c.sentido_contado == "saida":
                contados = len(self._saidas)
            else:
                contados = len(self._entradas | self._saidas)
            est_min = est_max = contados
            avisos.append("Linha virtual: conta apenas animais que cruzaram a linha com o rastreamento ativo. "
                          "Animais sobrepostos ou ocultos na fila podem não ser contados; o valor tende a "
                          "ficar abaixo do real em passagens apertadas.")
            if c.camera_em_movimento:
                avisos.append("Atenção: a linha só é confiável com a câmera PARADA. Se o drone se move, "
                              "a linha acompanha a imagem e a contagem perde o sentido.")
        else:
            contados = len(self._contados)
            est_min = est_max = contados
            avisos.append("Contagem por área de interesse: inclui apenas animais que passaram por ela. "
                          "Animais ocultos, agrupados ou fora do campo de visão podem não ser contados.")
        if self._pico > 0 and len(self._vistos) > 1.5 * self._pico and len(self._vistos) >= 5:
            avisos.append(f"Foram criados {len(self._vistos)} IDs, mas no máximo {self._pico} animais "
                          "apareceram ao mesmo tempo: possível fragmentação do rastreamento (IDs repetidos).")
        if self._reencontros:
            avisos.append(f"{self._reencontros} detecção(ões) reencontrada(s) após perda de rastreamento "
                          "(possíveis oclusões).")
        if self._sem_id:
            avisos.append(f"{self._sem_id} detecção(ões) sem ID de rastreamento não entram na contagem por ID.")

        return ResultadoContagem(
            estrategia=c.estrategia, detectados_quadro=self._detectados_quadro,
            ids_unicos=len(self._vistos), contados=contados,
            estimativa_min=est_min, estimativa_max=max(est_min, est_max),
            pico_simultaneo=self._pico, quadros_processados=self._quadros,
            entradas=entradas, saidas=saidas, avisos=avisos)
