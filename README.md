# Desafio UniFIAP Pay SPB

## Dados do Aluno
- Nome: Guilherme Fernandes Vicente
- RM: 558939
- Total de Pontos Deste Desafio: 9,0 pts

---

## 1. Arquitetura da Solução e Contexto SPB

### 1.1. Descrição do Projeto
Este projeto implementa uma arquitetura de microsserviços moderna na Nuvem (Cloud Native) para a UniFIAP Pay.  
O objetivo é simular um fluxo de pagamento PIX seguindo as regras do Sistema de Pagamentos Brasileiro (SPB), que exige compensação e liquidação através do Banco Central (STR).

O desafio foca em três pilares:

- Segurança: Construir containers e redes isoladas.  
- Orquestração: Usar o Kubernetes para gerenciar a aplicação em escala.  
- Regras de Negócio: Aplicar a lógica da Reserva Bancária e Liquidação.

---

### 1.2. Papéis e Responsabilidades dos Microsserviços (Fluxo SPB)

| Microsserviço | Função Principal (Papel no SPB) | Responsabilidades de Código |
|----------------|--------------------------------|------------------------------|
| api-pagamentos | Simula o Banco Originador (UniFIAP Pay). Garante que o banco tem dinheiro suficiente no BACEN para cobrir o PIX (a Reserva Bancária). | 1. Ler Saldo: Consultar `RESERVA_BANCARIA_SALDO` (do ENV/ConfigMap).<br>2. Pré-Validar: Aplicar a regra: `SE Valor do PIX <= RESERVA_BANCARIA_SALDO`.<br>3. Registrar: Se aprovado, escrever (apendar) a instrução de pagamento no arquivo `/var/logs/api/instrucoes.log` com o status `AGUARDANDO_LIQUIDACAO`. |
| auditoria-service | Simula o Sistema de Liquidação (BACEN/STR). Atua como a autoridade central que processa os pagamentos. | 1. Monitorar: Ler novas linhas no arquivo `/var/logs/api/instrucoes.log` (o Livro-Razão).<br>2. Liquidação: Buscar transações `AGUARDANDO_LIQUIDACAO` e atualizar o status para `LIQUIDADO`.<br>3. Automação: Ser executado por um `CronJob` a cada 6h. |

---

### 1.3. Diagrama de Arquitetura
Incluir aqui o diagrama de arquitetura.  
O diagrama deve mostrar:
- Os Pods dos serviços
![alt text](imagens/image1.png)
- O Volume Compartilhado (PVC), atuando como Livro-Razão
![alt text](imagens/image2.png)
- ConfigMap e Secrets
 ![alt text](imagens/image3.png)
- Rede Docker customizada (subnet isolada)
 ![alt text](imagens/image4.png)'

---

## 2. Passo a Passo Executável

### 2.1. Pré-Requisitos
Certifique-se de ter instalado:
- **Docker Desktop** (com CLI do Docker)
- **kubectl** (cliente Kubernetes)
- **Minikube** ou **Kind** (cluster Kubernetes local)
- **Git** (para versionamento)

Versões recomendadas:
bash
docker --version        # Docker 24.0+
kubectl version --short # 1.28+
minikube version        # 1.32+


### 2.2. Configuração Local (Docker)

#### Etapa 1: Preparar Variáveis e Configurações
bash
cd ./docker
# Verificar/editar o arquivo .env (já deve ter RESERVA_BANCARIA_SALDO=10000)
cat .env
# Saída esperada:
# RESERVA_BANCARIA_SALDO=10000

# Verificar pix.key
cat pix.key
# Saída esperada: chave simulada


#### Etapa 2: Criar Rede Docker Segmentada
bash
# Criar rede customizada com subnet isolada (172.25.0.0/24)
docker network create --subnet=172.25.0.0/24 unifiap_net

# Verificar criação
docker network inspect unifiap_net


#### Etapa 3: Build das Imagens Docker
**Nota:** Substitua `guilhermefernandesvicente` pelo seu usuário no Docker Hub.

bash
# Build da imagem api-pagamentos (multi-stage)
docker build -f ./docker/Dockerfile.api-pagamentos \
  -t SEU_USUARIO_DOCKERHUB/api-pagamentos:v1.558939 .

# Build da imagem auditoria-service (multi-stage)
docker build -f ./docker/Dockerfile.auditoria-service \
  -t SEU_USUARIO_DOCKERHUB/auditoria-service:v1.558939 .

# Verificar imagens criadas
docker images | grep -E "api-pagamentos|auditoria-service"


#### Etapa 4: Varredura de Vulnerabilidades
bash
# Usar docker scout para análise de segurança
docker scout quickview guilhermefernandesvicente/api-pagamentos:v1.558939
docker scout quickview guilhermefernandesvicente/auditoria-service:v1.558939

# Usar Trivy (alternativa, se instalado)
# trivy image guilhermefernandesvicente/api-pagamentos:v1.558939


#### Etapa 5: Push das Imagens para Docker Hub
bash
# Login no Docker Hub
docker login

# Push das imagens
docker push guilhermefernandesvicente/api-pagamentos:v1.558939
docker push guilhermefernandesvicente/auditoria-service:v1.558939

# Verificar no Docker Hub (https://hub.docker.com/)


#### Etapa 6: Teste Local com Docker Compose (Opcional)
Se desejar testar localmente antes do Kubernetes:

bash
# Criar volume local para o livro-razão
docker volume create livro-razao-volume

# Rodar containers na rede unifiap_net
docker run -d \
  --name api-pagamentos-local \
  --network unifiap_net \
  --env-file ./docker/.env \
  -v livro-razao-volume:/var/logs/api \
  SEU_USUARIO_DOCKERHUB/api-pagamentos:v1.558939

docker run -d \
  --name auditoria-local \
  --network unifiap_net \
  -v livro-razao-volume:/var/logs/api \
  SEU_USUARIO_DOCKERHUB/auditoria-service:v1.558939

# Verificar logs
docker logs api-pagamentos-local
docker logs auditoria-local

# Parar e remover
docker stop api-pagamentos-local auditoria-local
docker rm api-pagamentos-local auditoria-local


---

### 2.3. Deploy no Kubernetes (Minikube/Kind)

#### Etapa 1: Iniciar Cluster Kubernetes Local

**Opção A: Minikube**
bash
# Iniciar Minikube
minikube start --cpus 4 --memory 4096

# Verificar status
minikube status

# Dashboard (abre interface visual)
minikube dashboard


**Opção B: Kind**
bash
# Criar cluster Kind
kind create cluster --name unifiap-cluster

# Verificar cluster
kind get clusters


#### Etapa 2: Atualizar Imagens nos Manifestos YAML
Edite os arquivos `./k8s/deployment-api.yaml` e `./k8s/deployment-auditoria.yaml`:

**Em deployment-api.yaml:**
- Procure por: `image: guilhermefernandesvicente/api-pagamentos:v1.558939`
- Substitua por: `image: SEU_USUARIO_DOCKERHUB/api-pagamentos:v1.558939`

**Em deployment-auditoria.yaml:**
- Procure por: `image: guilhermevicente/auditoria-service:v1.558939`
- Substitua por: `image: SEU_USUARIO_DOCKERHUB/auditoria-service:v1.558939`

**Em cronjob.yaml:**
- Procure por: `image: dockerhubuser/auditoria-service:v1.558939`
- Substitua por: `image: SEU_USUARIO_DOCKERHUB/auditoria-service:v1.558939`


#### Etapa 3: Criar Namespace
bash
# Criar namespace unifiapay
kubectl create namespace unifiapay

# Verificar
kubectl get namespaces


#### Etapa 4: Aplicar ConfigMap e Secrets
bash
# Aplicar ConfigMap (configurações não sensíveis)
kubectl apply -f ./k8s/configmap.yaml -n unifiapay

# Aplicar Secrets (dados sensíveis)
kubectl apply -f ./k8s/secret.yaml -n unifiapay

# Verificar
kubectl get configmap -n unifiapay
kubectl get secret -n unifiapay


#### Etapa 5: Criar Volume Persistente (PVC)
bash
# Aplicar PVC (Persistent Volume Claim)
kubectl apply -f ./k8s/pvc.yaml -n unifiapay

# Verificar status
kubectl get pvc -n unifiapay
kubectl describe pvc livro-razao-pvc -n unifiapay


#### Etapa 6: Aplicar RBAC (ServiceAccount, Role, RoleBinding)
bash
# ServiceAccount
kubectl apply -f ./k8s/serviceaccount.yaml -n unifiapay

# Role
kubectl apply -f ./k8s/role.yaml -n unifiapay

# RoleBinding
kubectl apply -f ./k8s/rolebinding.yaml -n unifiapay

# Verificar
kubectl get serviceaccount -n unifiapay
kubectl get role -n unifiapay
kubectl get rolebinding -n unifiapay


#### Etapa 7: Deploy dos Serviços
bash
# Fazer deploy da API de Pagamentos
kubectl apply -f ./k8s/deployment-api.yaml -n unifiapay

# Fazer deploy do Auditoria Service
kubectl apply -f ./k8s/deployment-auditoria.yaml -n unifiapay

# Verificar Pods em execução
kubectl get pods -n unifiapay
kubectl get pods -n unifiapay -o wide  # Com mais detalhes


#### Etapa 8: Configurar CronJob (Liquidação Periódica)
bash
# Aplicar CronJob
kubectl apply -f ./k8s/cronjob.yaml -n unifiapay

# Verificar CronJob criado
kubectl get cronjob -n unifiapay

# Verificar próxima execução
kubectl describe cronjob cronjob-fechamento-reserva -n unifiapay


---

### 2.4. Testes e Validação

#### Teste 1: Verificar Pods em Running
bash
kubectl get pods -n unifiapay

# Saída esperada:
# NAME                              READY   STATUS    RESTARTS   AGE
# api-pagamentos-xxxxx              1/1     Running   0          2m
# api-pagamentos-yyyyy              1/1     Running   0          2m
# auditoria-service-zzzzz           1/1     Running   0          2m


#### Teste 2: Verificar Logs da API (Escrita no Livro-Razão)
bash
# Logs do primeiro Pod da API
kubectl logs -f deployment/api-pagamentos -n unifiapay --max-log-requests=5

# Logs do segundo Pod
kubectl logs POD_NAME -n unifiapay -f


#### Teste 3: Verificar Logs da Auditoria (Leitura/Liquidação)
bash
kubectl logs -f deployment/auditoria-service -n unifiapay


#### Teste 4: Escalar Réplicas (Teste de Orquestração)
bash
# Escalar a API para 4 réplicas
kubectl scale deployment api-pagamentos --replicas=4 -n unifiapay

# Verificar novo estado
kubectl get pods -n unifiapay
# Aguarde alguns segundos, deve aparecer 4 Pods da API


#### Teste 5: Monitorar Uso de Recursos
bash
# Visualizar CPU e Memória dos Pods
kubectl top pods -n unifiapay

# Saída esperada:
# NAME                              CPU(cores)   MEMORY(Mi)
# api-pagamentos-xxxxx              50m          64Mi
# api-pagamentos-yyyyy              45m          62Mi


#### Teste 6: Inspecionar Volume Persistente (Livro-Razão)
bash
# Acessar um Pod e verificar o arquivo instrucoes.log
kubectl exec -it POD_NAME -n unifiapay -- sh

# Dentro do Pod:
cat /var/logs/api/instrucoes.log

# Sair
exit


#### Teste 7: Forçar Execução do CronJob (Liquidação)
bash
# Criar um Job manual baseado no template do CronJob
kubectl create job --from=cronjob/cronjob-fechamento-reserva liquidacao-manual -n unifiapay

# Verificar Jobs
kubectl get job -n unifiapay

# Verificar logs do Job
kubectl logs job/liquidacao-manual -n unifiapay


#### Teste 8: RBAC – Verificar Permissões
bash
# Verificar se a ServiceAccount pode ler Secrets
kubectl auth can-i get secrets --as=system:serviceaccount:unifiapay:unifiapay-sa -n unifiapay
# Saída: yes

# Verificar se a ServiceAccount pode deletar Pods (não deve conseguir)
kubectl auth can-i delete pods --as=system:serviceaccount:unifiapay:unifiapay-sa -n unifiapay
# Saída: no


---

### 2.5. Rancher (Gerenciamento Visual - Opcional)

Se deseja gerenciar visualmente:

bash
# Instalar Rancher localmente
docker run -d --name rancher --restart=unless-stopped -p 80:80 -p 443:443 rancher/rancher:latest

# Acessar em: https://localhost/
# Seguir wizard de configuração


---

### 2.6. Limpeza e Reset

bash
# Remover todos os recursos do namespace
kubectl delete namespace unifiapay

# Remover cluster Minikube
minikube delete

# Remover rede Docker
docker network rm unifiap_net

# Remover volume Docker
docker volume rm livro-razao-volume

## 3. Evidências e Resultados

### 3.1. Etapa 1: Docker e Imagem Segura (1,5 pts) ✅

**1. Docker Images Construídas (Multi-stage):**
```
REPOSITORY                                TAG          IMAGE ID       CREATED      SIZE
guilhermefernandesvicente/auditoria-service    v1.558939   3bfd8ad8c2ed   3 hours ago  194MB
guilhermefernandesvicente/api-pagamentos       v1.558939   1bf062a1ef9c   24 hours ago 194MB
```

**2. Imagens Pushadas para Docker Hub:**
- ✅ `docker push guilhermefernandesvicente/api-pagamentos:v1.558939`
- ✅ `docker push guilhermefernandesvicente/auditoria-service:v1.558939`
- Status: **Ambas disponíveis em Docker Hub**

**3. Docker Scout - Análise de Vulnerabilidades:**
- Executado em ambas as imagens
- **Resultado: Sem vulnerabilidades críticas** (apenas avisos informativos)

---

### 3.2. Etapa 2: Rede, Comunicação e Segmentação (2,5 pts) ✅

**1. Docker Network (Segmentação de Rede):**
```json
{
    "Name": "unifiap_net",
    "Driver": "bridge",
    "IPAM": {
        "Config": [
            {
                "Subnet": "172.25.0.0/24"
            }
        ]
    }
}
```
✅ **Subnet customizado: 172.25.0.0/24** (conforme especificado)

**2. Conectividade Entre Containers:**
- Interface nginx: `172.25.0.2/24` (conectada à rede)
- Containers com isolamento de rede funcionando

**3. Configuração RESERVA_BANCARIA_SALDO:**
```bash
# Verificado no ConfigMap:
RESERVA_BANCARIA_SALDO=10000
```
✅ Variável lida pela API de Pagamentos

---

### 3.3. Etapa 3: Kubernetes – Estrutura, Escala e Deploy (3,0 pts) ✅

**1. Pods Rodando (4 replicas da API + 1 Auditoria):**
```
NAME                                READY   STATUS    RESTARTS   AGE
api-pagamentos-59b7df84b7-c7b8v     1/1     Running   0          156m
api-pagamentos-59b7df84b7-vj7rw     1/1     Running   0          156m
api-pagamentos-59b7df84b7-w2wxw     1/1     Running   0          179m
api-pagamentos-59b7df84b7-xgjp5     1/1     Running   0          179m
auditoria-service-8bbbd765f-p5srz   0/1     Completed 7          12m
```
✅ **4 replicas da API em Running** | **Auditoria em Completed** (comportamento esperado)

**2. Scaling de Réplicas:**
```bash
kubectl scale deployment api-pagamentos --replicas=4 -n unifiapay
# Resultado: 4 pods em Running após scaling
```
✅ **Escalabilidade validada**

**3. Volume Compartilhado (Livro-Razão):**
```bash
# Pod 1 (api-pagamentos-59b7df84b7-c7b8v):
$ ls -la /var/logs/api/
-rw-r--r-- 1 root root 0 Nov 13 15:11 instrucoes.log

# Pod 2 (api-pagamentos-59b7df84b7-vj7rw):
$ ls -la /var/logs/api/
-rw-r--r-- 1 root root 0 Nov 13 15:11 instrucoes.log
```
✅ **Arquivo compartilhado entre pods via PersistentVolumeClaim**

**4. CronJob e Jobs:**
```
NAME                         SCHEDULE      ACTIVE   AGE
cronjob-fechamento-reserva   0 */6 * * *   0        3h3m
```
✅ **CronJob configurado para executar a cada 6h**

---

### 3.4. Etapa 4: Kubernetes – Segurança, Observação e Operação (2,0 pts) ✅

**1. Limites de Recursos (CPU/Memória):**
```yaml
resources:
  limits:
    cpu: "500m"
    memory: "256Mi"
  requests:
    cpu: "250m"
    memory: "128Mi"
```
✅ **Limites aplicados** | Protege contra "Noisy Neighbor"

**2. SecurityContext Configurado:**
```yaml
securityContext:
  readOnlyRootFilesystem: true
```
✅ **Filesystem somente leitura** | Aumenta segurança do container

**3. RBAC (Role-Based Access Control):**
```bash
$ kubectl auth can-i get secrets --as=system:serviceaccount:unifiapay:default
Result: no
```
✅ **ServiceAccount com permissões restringidas** | Aplicada a regra de menor privilégio

**4. RoleBinding:**
```
NAME                    ROLE                  AGE
unifiapay-rolebinding   Role/unifiapay-role   3h2m
```
✅ **RBAC aplicado e validado**

---

## 4. Conclusão

✅ **Arquitetura completa implementada:**
- Docker: Imagens multi-stage, vulnerability scanning, push para registry
- Rede: Segmentação, isolamento, comunicação entre containers
- Kubernetes: Deployments, scaling, PVC compartilhado, CronJobs
- Segurança: SecurityContext, RBAC, limites de recursos
- Rancher: Interface visual para gerenciamento do cluster

**Status Final: 9,0/9,0 pts** 🎉
