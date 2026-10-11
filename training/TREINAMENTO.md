# Guia de treinamento do modelo de bovinos

Nenhum modelo treinado acompanha o projeto. Siga estes passos quando tiver seus vídeos.
Todos os comandos são executados na pasta do projeto, com o ambiente ativado:
`.\.venv\Scripts\Activate.ps1`

## 1. Gravar bons vídeos
- Câmera apontada para baixo (90°), sem zoom, velocidade baixa e constante.
- Altura constante em cada voo. Faça voos em alturas diferentes (ex.: 40, 60, 80 m), em dias/horários e pastos variados.
- Evite sombras longas e contraluz forte.
- Em pelo menos um voo, **conte os animais manualmente**: serve para validar o resultado.
- Muitos voos diferentes valem mais do que um voo longo.

## 2. Extrair quadros
```powershell
python training/extrair_quadros.py data/videos/voo1.mp4 --a_cada 30
```
Gera imagens em `data/datasets/bovinos/brutas/voo1/`. Escolha o intervalo para que quadros seguidos não sejam quase idênticos.

## 3. Anotar (caixa em cada animal)
Use uma ferramenta de anotação, por exemplo **CVAT** (cvat.ai) ou **LabelImg**/**Label Studio**.
- Uma única classe: `bovino`.
- Marque **todos** os animais visíveis; animal não marcado ensina o modelo a ignorá-lo.
- Exporte no formato **YOLO**: um `.txt` por imagem, com o mesmo nome.
- Coloque imagem + `.txt` juntos em `data/datasets/bovinos/anotadas/`.

Ponto de partida realista: algumas centenas de imagens com vários animais cada.

## 4. Dividir em treino / validação / teste
```powershell
python training/dividir_dataset.py data/datasets/bovinos/anotadas
```
A divisão é feita **por voo**, para evitar que quadros quase iguais caiam em treino e teste ao mesmo tempo (isso inflaria os resultados). Com menos de 3 voos o script avisa. Gera `data/datasets/bovinos/yolo/data.yaml`.

## 5. Treinar
```powershell
python training/treinar.py data/datasets/bovinos/yolo/data.yaml
```
Opções: `--epocas 100`, `--tamanho 1280` (animais pequenos), `--lote 4` (se faltar memória da GPU).
O script avalia no conjunto de **teste** e copia o melhor modelo para `models/bovinos.pt`.

## 6. Validar de verdade
As métricas do passo 5 só valem para imagens parecidas com as do treino. Faça o teste final:
rode o app em um voo **novo**, com contagem manual feita por você, e compare.

## 7. Usar na aplicação
Com `models/bovinos.pt` presente, o app carrega o modelo automaticamente ao iniciar um vídeo.
Sem o arquivo, o app exibe o aviso e mostra só o vídeo.
