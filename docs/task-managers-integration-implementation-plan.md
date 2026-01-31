# План реализации: Интеграция с Task Managers

Документ описывает пошаговый план реализации интеграции с системами управления задачами (GitHub Issues, и в будущем — Jira, Linear и др.) согласно [спецификации](./task-managers-integration.md).

## Структура плана

План разбит на **две части**:

- **I. MVP** — что реализовано и актуальное состояние
- **II. SECOND ITERATION** — задачи для следующей итерации (вынесены в конец документа)

---

План MVP разбит на три фазы:
1. **Garage (Frontend)** — UI для настройки интеграции и управления задачами
2. **API (Backend)** — GraphQL API для работы с интеграциями
3. **Workers (Background tasks)** — Автоматическое создание задач по расписанию

Тесты пишутся сразу после реализации соответствующего функционала, а не в конце.

---

## I. MVP

### Фаза 1: Garage (Frontend)

### 1.1. Добавление нового пункта меню в настройках проекта

**Задача:** Добавить пункт "Task Manager" в меню настроек проекта

**Файлы:**
- `garage/src/components/project/settings/Layout.vue`

**Действия:**
- Добавить новый `router-link` в меню настроек после `project-settings-integrations`
- Создать соответствующий маршрут в `garage/src/router.ts`

**Тесты:** Не требуется (UI компонент)

---

### 1.2. Создание компонента страницы настройки Task Manager

**Задача:** Создать основной компонент для страницы настройки интеграции

**Файлы:**
- `garage/src/components/project/settings/TaskManagerIntegration.vue` (новый файл)

**Действия:**
- Создать компонент по аналогии с `General.vue` и `Integrations.vue`
- Добавить секцию для подключения GitHub репозитория
- Добавить секцию "Auto Task Creation" с полем для ввода порога
- Добавить секцию "Agent" с переключателем для назначения агента
- Использовать Vuex store для получения проекта и вызова мутаций
- Добавить локализацию в `garage/src/i18n/messages/en.json` и `ru.json`

**Тесты:** Не требуется (UI компонент)

---

### 1.3. Компонент подключения GitHub репозитория

**Задача:** Реализовать UI для подключения GitHub репозитория через GitHub App

**Файлы:**
- `garage/src/components/project/settings/TaskManagerIntegration.vue`

**Действия:**
- Добавить кнопку "Connect GitHub Repository"
- При клике перенаправлять на Hawk API endpoint `/integration/github/connect?projectId=<projectId>`
  - API endpoint будет обрабатывать редирект на GitHub
  - При отправке запроса нужно передать авторизационные данные через Заголовок Authorization с токеном пользователя.
- **Обработать query параметр `apiError`** — отображение ошибки подключения:
  - API при ошибке редиректит в Garage на главную с GET-параметром `?apiError=<сообщение>`
  - Garage обрабатывает это в `App.vue` через метод `handleApiErrorFromQuery()`:
    - Читает `this.$route.query.apiError`
    - Показывает уведомление через `notifier.show({ message: apiError, style: 'error' })`
    - Удаляет `apiError` из URL после показа
  - После редиректа с ошибкой пользователь оказывается на главной (`/`) с показанным уведомлением
- После успешного подключения (после callback redirect) отображать:
  - `Connected to owner/repo`
  - Кнопка "Disconnect"
- Реализовать логику отображения состояния подключения
- Обработать query параметры успеха/ошибки после callback
- **Запрос списка репозиториев и выбор репозитория** (после callback):
  - Запросить список репозиториев через API (`getRepositoriesForInstallation`, нужен endpoint или GraphQL)
  - Показать UI для выбора репозитория из списка
  - Сохранить выбранный репозиторий в конфигурации проекта

**Зависимости:** API должен предоставлять endpoint `/integration/github/connect` для редиректа на GitHub и `/integration/github/callback` для обработки callback; API endpoint или GraphQL query для получения списка репозиториев

**Тесты:** Не требуется (UI компонент)

---

### 1.4. Реализация кнопки Disconnect

**Задача:** Реализовать функциональность отключения GitHub интеграции

**Файлы:**
- `garage/src/components/project/settings/TaskManagerIntegration.vue`

**Действия:**
- Реализовать работу кнопки "Disconnect":
  - При клике показывать окно подтверждения (ConfirmationWindow) с описанием действия
  - Использовать `ActionType.SUBMIT` для типа действия
  - При подтверждении вызывать GraphQL мутацию `disconnectTaskManager(projectId: ID!)`
  - После успешного отключения:
    - Обновить данные проекта в Vuex store
    - Обновить UI: убрать информацию о подключенном репозитории, показать кнопку "Connect GitHub Repository"
    - Показать уведомление об успехе через `notifier.show()`
  - При ошибке отключения:
    - Показать уведомление об ошибке через `notifier.show()`
  - Кнопка должна быть доступна только для workspace admin (проверка через `isAdmin` computed property)

**Зависимости:** 
- GraphQL мутация `disconnectTaskManager` должна быть реализована в API (см. раздел 2.6)

**Тесты:** Не требуется (UI компонент)

---

### 1.5. Компонент настроек автосоздания задач

**Задача:** UI для настройки автоматического создания задач

**Файлы:**
- `garage/src/components/project/settings/TaskManagerIntegration.vue`

**Действия:**
- Добавить поле ввода "Create Issue when total repeats ≥ N"
  - Тип: `number`, минимальное значение: 1
  - Валидация через Vue компонент
- Добавить описание: *Uses total number of error repetitions for all time (**`totalCount`**).*
- Сохранять изменения через GraphQL мутацию `updateTaskManagerSettings`

**Тесты:** Не требуется (UI компонент)

---

### 1.6. Компонент настройки агента

**Задача:** UI для включения/выключения назначения агента на задачи

**Файлы:**
- `garage/src/components/project/settings/TaskManagerIntegration.vue`

**Действия:**
- Добавить переключатель "Assign agent to new tasks"
- Использовать `forms/UiSwitch.vue`
- Добавить описание: *If the agent is unavailable, the task will be created without an assignee.*
- Сохранять изменения через GraphQL мутацию `updateTaskManagerSettings`

**Тесты:** Не требуется (UI компонент)

---

### 1.7. Добавление блока Task Manager на странице Event

**Задача:** Показать блок с задачами на странице деталей ошибки

**Файлы:**
- Компонент страницы события `EventHeader.vue`

**Действия:**
- Кнопки должны быть добавлены в блок `event-header__buttons` — по правому краю
- В MVP: отображение состояния "задача существует"
  - Если `taskManagerItem` существует → показать кнопку-ссылку "Issue #123"
- Добавить информацию о `taskManagerItem` в существующие query Event

**Тесты:** Не требуется (UI компонент)

---

### 1.8. Добавление GraphQL запросов и мутаций в Garage

**Задача:** Добавить GraphQL операции для работы с Task Manager

**Файлы:**
- `garage/src/api/` (нужно найти где хранятся GraphQL запросы)
- Возможно, `garage/src/api/queries.ts` или `garage/src/api/mutations.ts`

**Действия:**
- Добавить `taskManager` в существующие query Project
- Добавить мутации:
  - `disconnectTaskManager`
  - `updateTaskManagerSettings`
- Обновить фрагменты GraphQL для Event, если нужно включить `taskManagerItem`

**Примечание:** Подключение GitHub репозитория происходит через HTTP endpoint `/integration/github/connect`, а не через GraphQL мутацию. Garage должен редиректить на этот endpoint. При этом нужно передать заголовок Authorization с токеном пользователя.

**Тесты:** Не требуется (GraphQL клиент)

---

### 1.9. Обновление типов TypeScript в Garage

**Задача:** Добавить типы для Task Manager в проект и события

**Файлы:**
- `garage/src/types/project.ts`
- `garage/src/types/events.ts` (или аналогичный)

**Действия:**
- Добавить тип `TaskManager` в тип `Project`
- Добавить тип `TaskManagerItem` в тип `Event`
- Создать интерфейсы для всех структур данных согласно спецификации. Если интерфейс будет нужен еще в АПИ (или воркерах), то его нужно добавить в пакет [@hawk.so/types](../types)

**Тесты:** TypeScript компиляция

---

### 1.10. Обновление локализации

**Задача:** Добавить переводы для всех новых UI элементов

**Файлы:**
- `garage/src/i18n/messages/en.json`
- `garage/src/i18n/messages/ru.json`

**Действия:**
- Добавить ключи для:
  - Название раздела "Task Manager Integration"
  - Кнопки подключения/отключения
  - Поля настроек
  - Сообщения об ошибках
  - Сообщения об успехе

**Тесты:** Не требуется (локализация)

---

### Фаза 2: API (Backend)

### 2.1. Создание GitHub App и настройка

**Задача:** Создать и настроить GitHub App для интеграции

**Действия:**

#### 2.1.1. Создание GitHub App

1. Перейти на https://github.com/settings/apps
2. Нажать "New GitHub App"
3. Заполнить форму:
   - **GitHub App name:** Hawk Error Tracker (или другое имя)
   - **Homepage URL:** `https://hawk.so` (или production URL)
   - **User authorization callback URL:** `https://api.hawk.so/integration/github/oauth`
     - ⚠️ **Важно:** Этот URL используется для OAuth flow получения user-to-server токенов
     - Без этого токена невозможно назначить Copilot на задачи
   - **Setup URL:** Оставить пустым (не используется)
     - У нас уже есть Callback URL для обработки установки
     - Setup URL избыточен, так как callback уже обрабатывает редирект
   - **Webhook URL:** `https://api.hawk.so/integration/github/webhook` (или соответствующий URL для окружения)
   - **Webhook secret:** заполнить
     - Сгенерировать криптографически стойкую случайную строку (например, через `openssl rand -hex 32` или онлайн-генератор)
     - Сохранить этот секрет в переменные окружения (см. раздел 2.1.2)
     - Используется для проверки подписи webhook от GitHub (HMAC SHA-256) в целях безопасности
     - Без этого секрета невозможно будет проверить, что webhook действительно пришел от GitHub
   - **SSL verification:** Оставить включенным (по умолчанию)
     - GitHub проверяет SSL сертификат вашего webhook endpoint при отправке webhook'ов
     - Это защищает от MITM атак и обеспечивает безопасность передачи данных
     - Отключать только в development/testing окружении с self-signed сертификатами
     - В production всегда должен быть включен для безопасности
   - **Repository permissions:**
     - **Issues:** Read & Write
     - **Metadata:** Read-only (автоматически)
   - **Subscribe to events:**
     - **Installation** — обязательно подписаться
       - Нужно для обработки события `installation.deleted` (когда пользователь удаляет установку App)
       - Также позволяет отслеживать другие события установки (`installation.created`, `installation.suspend` и т.д.) для мониторинга
       - Без подписки на это событие мы не сможем автоматически очистить конфигурацию при удалении установки
     - Остальные события (Issues, Issue comment, Label и т.д.) — НЕ подписываться
       - Мы только создаем issues, но не обрабатываем изменения в них
       - Подписка на эти события не нужна для нашей функциональности
   - **Redirect on update:** Можно поставить галочку (опционально)
     - При включенной опции OAuth эта опция перенаправляет пользователя на **User authorization callback URL** (не Setup URL) при обновлении установки (добавление/удаление репозиториев)
     - Это позволяет автоматически обновить OAuth токены при изменении установки
     - Если галочка не стоит, пользователю нужно будет вручную переустановить приложение для обновления токенов
   - **Request user authorization (OAuth) during installation:** ✅ **Обязательно включить**
     - ⚠️ **Критически важно:** Эта опция необходима для получения user-to-server OAuth токенов
     - Без этой опции невозможно назначить Copilot на задачи, так как назначение требует user-level permissions
     - При включении этой опции GitHub будет запрашивать у пользователя разрешение во время установки приложения
     - После установки GitHub перенаправит на `User authorization callback URL` с authorization code
     - Hawk обменивает code на access token и refresh token, которые сохраняются в `project.taskManager.config.delegatedUser`
   - **Where can this GitHub App be installed?**
     - Выбрать "Only on this account" или "Any account" в зависимости от требований

5. **Сделать приложение публичным** (если нужна установка на сторонние аккаунты):
   - Перейти в аккаунт, которому принадлежит App → **Settings** → **Developer settings** → **GitHub Apps** → выбрать App → **Edit**
   - Раздел **Advanced** → **Danger zone** → **Make public**
   - Без этого приложение можно установить только в аккаунте владельца

6. После создания сохранить:
   - **App ID** (например: `123456`)
   - Сгенерировать и сохранить **Private key** (Client secrets)

#### 2.1.2. Настройка в Hawk

**Файлы:**
- `api/.env.sample` — актуальный список переменных
- `.env` для каждой среды (development, staging, production)

**Действия:**
- Добавить переменные окружения (сверяться с `api/.env.sample`):
  ```env
  # GitHub App settings
  GITHUB_APP_ID=1234567
  GITHUB_APP_CLIENT_ID=Iv23li65HEIkWZXsm6qO
  GITHUB_APP_CLIENT_SECRET=...
  GITHUB_APP_SLUG=hawk-tracker-app

  # Private key — только одна строка с \n (многострочные значения в k8s не поддерживаются)
  GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n...\n-----END RSA PRIVATE KEY-----"
  
  # Webhook secret для проверки подлинности webhook от GitHub
  GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

  # URLs (используются для OAuth redirect и installation URL)
  API_URL=http://localhost:4000
  GARAGE_URL=http://localhost:8080
  ```
  
  **Важно:** `GITHUB_PRIVATE_KEY`:
  - Поддерживается **только одна строка** с экранированными `\n` (не многострочное значение)
  - В k8s и некоторых окружениях многострочные значения не работают — все переносы сливаем в одну строку с `\n`
  - В коде метод `getPrivateKey()` преобразует `\n` в реальные переносы: `privateKey.replace(/\\n/g, '\n')`

---

### 2.2. Установка зависимостей для работы с GitHub API

**Задача:** Добавить библиотеки для работы с GitHub API

**Файлы:**
- `api/package.json`

**Действия:**
- Установить `@octokit/rest` или `@octokit/auth-app` для работы с GitHub API
- Установить `jsonwebtoken` для создания JWT токенов для GitHub App

```bash
cd api
yarn add @octokit/rest @octokit/auth-app @octokit/auth-oauth-app jsonwebtoken
```

---

### 2.3. Создание сервиса для работы с GitHub API

**Задача:** Создать сервис для взаимодействия с GitHub API

**Файлы:**
- `api/src/integrations/github/service.ts`

**Действия:**
- Создать класс `GitHubService`:
  - Приватный метод `getPrivateKey(): string` — получение приватного ключа из переменных окружения
    - Проверить наличие `GITHUB_PRIVATE_KEY`
    - Если `GITHUB_PRIVATE_KEY` — обработать значение (поддерживает оба формата):
      - Если значение уже содержит реальные переносы строк (Вариант 1) — использовать как есть
      - Если значение содержит экранированные `\n` (Вариант 2) — преобразовать в реальные переносы строк
        - Обычно `dotenv` делает это автоматически, но для надежности можно использовать `privateKey.replace(/\\n/g, '\n')`
        - Или проверить, содержит ли строка литеральные `\n` (не переносы строк), и заменить их
    - Вернуть приватный ключ в формате PEM с реальными переносами строк
  - Приватный метод `createInstallationToken(installationId: string): Promise<string>` — получение installation access token от GitHub API
    - Получить приватный ключ через `getPrivateKey()`
    - Создать JWT токен для GitHub App (используя `GITHUB_APP_ID` и приватный ключ)
    - Делает POST запрос на `https://api.github.com/app/installations/{installationId}/access_tokens`
    - Возвращает installation access token для работы с GitHub API от имени установленного приложения
    - Токен действителен 1 час, затем нужно запросить новый
  - Метод `createIssue(repoFullName: string, installationId: string, issueData: IssueData): Promise<GitHubIssue>` — создание issue
    - Внутри метода вызывается `createInstallationToken(installationId)` для получения токена
    - Использует **installation access token** для создания issue через GitHub REST API
    - Issue создается **от имени GitHub App** (не от имени пользователя)
  - Метод `assignCopilot(repoFullName: string, issueNumber: number, delegatedUserToken: string): Promise<void>` — назначение Copilot
    - ⚠️ **Важно:** Использует **user-to-server OAuth token** (не installation token)
    - Принимает `delegatedUserToken` из `project.taskManager.config.delegatedUser.accessToken`
    - Использует user token для назначения Copilot через GitHub GraphQL API
    - Назначение выполняется **от имени авторизованного пользователя** (требуется для Copilot)
    - Если токен истек (401), автоматически обновляет токен через `refreshUserToken` и повторяет операцию
  - Метод `getInstallationUrl(state: string): string` — генерация URL для установки GitHub App
    - Генерирует URL для перенаправления пользователя на GitHub для установки App: `https://github.com/apps/<app-name>/installations/new?state=<state>`
    - `state` параметр передается как есть (не модифицируется внутри метода)
  - Метод `getInstallationForRepository(installationId: string): Promise<Installation>` — получение информации об установке (опционально, если нужно проверить/обновить данные)
    - Создать JWT через `createJWT()`
    - Делает GET запрос на `https://api.github.com/app/installations/{installationId}`
    - Возвращает информацию об аккаунте (login, type), target_type, permissions
  - Метод `getRepositoriesForInstallation(installationId: string): Promise<Repository[]>` — список репозиториев установки
    - Вызвать `createInstallationToken(installationId)` для получения токена
    - Использовать `octokit.paginate(octokit.rest.apps.listReposAccessibleToInstallation)` для получения всех репозиториев
    - Преобразовать в тип `Repository[]` (id, name, fullName, private, htmlUrl, updatedAt, language)
    - Для UI выбора репозитория в Garage
  - Метод `deleteInstallation(installationId: string): Promise<void>` — удаление установки GitHub App
    - Создать JWT, вызвать `octokit.rest.apps.deleteInstallation`
    - Используется при кнопке Disconnect (отключение App из аккаунта пользователя)
  - Метод `exchangeOAuthCodeForToken(code: string, redirectUri?: string): Promise<...>` — обмен OAuth code на user-to-server токены
    - Использовать `exchangeWebFlowCode` из `@octokit/oauth-methods` (clientType: 'github-app')
    - redirectUri по умолчанию: `${API_URL}/integration/github/oauth`
    - Возвращает accessToken, refreshToken, expiresAt, user. Вызывается в callback после установки App с "Request user authorization"
  - Метод `validateUserToken(accessToken: string): Promise<{ valid, user?, status }>` — проверка валидности user token
    - GET `/user` через Octokit. При 401/403 вернуть `{ valid: false, status: 'revoked' }`
    - Для проверки токена перед операциями с Copilot
  - Метод `refreshUserToken(refreshToken: string): Promise<...>` — обновление истёкшего access token
    - Использовать `refreshToken` из `@octokit/oauth-methods`
    - Возвращает новый accessToken, refreshToken, expiresAt
    - Вызывать при 401 при `assignCopilot` для повторной попытки

**Тесты:**
- `api/test/integrations/github.test.ts`
- Тесты для всех методов с моками GitHub API

---

### 2.4. Обновление TypeScript типов для Project

**Задача:** Добавить типы для `taskManager` в Project

**Файлы:**
- `types/src/dbScheme/project.ts`

**Действия:**
- Добавить интерфейс `TaskManagerConfig` в `types/src/dbScheme/project.ts`:
  ```typescript
  /**
   * Task Manager configuration for project
   */
  export interface TaskManagerConfig {
    /**
     * Type of task manager (currently only 'github' is supported)
     */
    type: 'github';
    
    /**
     * Enable automatic task creation by scheduled worker
     */
    autoTaskEnabled: boolean;
    
    /**
     * Threshold for auto task creation (minimum totalCount)
     */
    taskThresholdTotalCount: number;
    
    /**
     * Assign agent (e.g. Copilot) to newly created tasks
     */
    assignAgent: boolean;
    
    /**
     * Usage tracking for daily auto-task budget
     */
    usage?: {
      /**
       * UTC day boundary (e.g. 2026-01-17T00:00:00.000Z)
       */
      dayStartUtc: Date;
      
      /**
       * Number of auto-created tasks since dayStartUtc
       */
      autoTasksCreated: number;
    };
    
    /**
     * Date when integration was connected
     */
    connectedAt: Date;
    
    /**
     * Date when configuration was last updated
     */
    updatedAt: Date;
    
    /**
     * Task manager specific configuration (typed by `type`)
     */
    config: {
      /**
       * GitHub App installation ID
       */
      installationId: string;
      
      /**
       * Repository ID
       */
      repoId: string | number;
      
      /**
       * Repository full name (owner/repo)
       */
      repoFullName: string;
    };
  }
  ```
- Экспортировать интерфейс из `types/src/dbScheme/project.ts` (или создать отдельный файл `types/src/dbScheme/taskManager.ts` если планируется расширение для других типов)
- Добавить поле `taskManager?: TaskManagerConfig` в `ProjectDBScheme`
- Убедиться, что тип экспортирован из `types/index.ts` если используется централизованный экспорт
- Увеличить минорную версию проекта в `package.json`

**Тесты:** TypeScript компиляция

---

### 2.5. Обновление GraphQL схемы для Project

**Задача:** Добавить типы и мутации для Task Manager в GraphQL схему

**Файлы:**
- `api/src/typeDefs/project.ts`
- `api/src/typeDefs/taskManager.ts` (новый файл) — для типов
- `api/src/typeDefs/projectTaskManagerMutations.ts` (новый файл) — для мутаций

**Действия:**
- Создать `api/src/typeDefs/taskManager.ts`:
  - Тип `TaskManager`
  - Тип `TaskManagerUsage`
  - Тип `GitHubTaskManagerConfig`
- Обновить `api/src/typeDefs/project.ts`:
  - Добавить поле `taskManager: TaskManager` в тип `Project`
- Создать `api/src/typeDefs/projectTaskManagerMutations.ts`:
  - Input типы для мутаций:
    - `UpdateTaskManagerSettingsInput`
  - Мутации в `extend type Mutation`:
    - `disconnectTaskManager(projectId: ID!): Project! @requireAdmin`
    - `updateTaskManagerSettings(input: UpdateTaskManagerSettingsInput!): Project! @requireAdmin`
- Добавить импорты в `api/src/typeDefs/index.ts`:
  - Импортировать `taskManager` типы
  - Импортировать `projectTaskManagerMutations`

**Примечание:** Подключение GitHub репозитория происходит через HTTP endpoint `/integration/github/connect`, а не через GraphQL мутацию. См. раздел 2.7.

**Тесты:**
- Тест схем в проекте нет

---

### 2.6. Реализация GraphQL резолверов для Project

**Задача:** Реализовать резолверы для Task Manager мутаций проекта

**Файлы:**
- `api/src/resolvers/project.js` (обновить)

**Действия:**
- Добавить резолверы в `Mutation` секцию `project.js`:
  - `disconnectTaskManager` — отключение интеграции
    - Удаляет `taskManager` из проекта
    - Обновляет `updatedAt`
  - `updateTaskManagerSettings` — обновление настроек
    - Обновляет `autoTaskEnabled`, `taskThresholdTotalCount`, `assignAgent`
    - Обновляет `updatedAt`
- Добавить резолвер для поля `taskManager` в `Project` type (если нужно преобразование данных)

**Примечание:** Подключение GitHub репозитория происходит через HTTP endpoint `/integration/github/connect`, а не через GraphQL мутацию. См. раздел 2.7.

**Тесты:**
- `api/test/resolvers/project.test.ts` (дополнить существующие тесты)
- Интеграционные тесты для мутаций `disconnectTaskManager` и `updateTaskManagerSettings`
- Тесты валидации входных данных
- Тесты проверки прав доступа (@requireAdmin)

---

### 2.7. Создание HTTP endpoint для инициации подключения GitHub

**Задача:** Реализовать endpoint для инициации подключения GitHub репозитория

**Файлы:**
- `api/src/integrations/github/routes.ts` (новый файл) — файл с роутами Express
- `api/src/index.ts` (обновить для регистрации routes)

**Действия:**
- Создать функцию `createGitHubRouter` или класс `GitHubRoutes` в `api/src/integrations/github/routes.ts`:
  - Создать Express Router с помощью `express.Router()`
  - Добавить обработчик для endpoint `GET /connect` (полный путь: `/integration/github/connect`)
  - Экспортировать функцию для получения router или класс с методом `getRouter()`
- Зарегистрировать роуты в `api/src/index.ts`:
  - Импортировать функцию/класс из `./integrations/github/routes`
  - В конструкторе `HawkAPI` (после инициализации middleware, но до GraphQL) добавить:
    ```typescript
    const githubRouter = createGitHubRouter(); // или new GitHubRoutes().getRouter()
    this.app.use('/integration/github', githubRouter);
    ```
  - Альтернативно: создать функцию `appendGitHubRoutes` по аналогии с `appendSsoRoutes` и вызвать в `start()`
- Создать endpoint `GET /integration/github/connect?projectId=<projectId>`:
  - Принять `projectId` из query параметров
  - Проверить права пользователя (только admin workspace может подключать интеграцию)
  - **Создать `state` параметр для CSRF защиты:**
    - **Генерация:** Создать уникальный `state` одним из способов:
      - **Вариант 1:** JWT токен, подписанный секретным ключом, содержащий:
        - `projectId` (для идентификации проекта)
        - `userId` (для проверки, что тот же пользователь завершает flow)
        - `timestamp` (для истечения срока действия, например, 10-15 минут)
        - Случайную строку (`nonce`) для уникальности
      - **Вариант 2:** Случайная криптографически стойкая строка (UUID v4 или `crypto.randomBytes`)
        - В этом случае `state` сохраняется в Redis/сессию вместе с данными: `{ projectId, userId, timestamp }`
        - `state` используется как ключ для поиска этих данных в callback
    - **Сохранение:** Сохранить `state` во временное хранилище (Redis предпочтительно) с TTL 15-30 минут:
      - Если используется JWT: можно хранить только `state` в Redis как ключ с данными, или валидировать JWT напрямую
      - Если используется случайная строка: сохранить как ключ с данными `{ projectId, userId, timestamp }`
  - Сгенерировать GitHub installation URL через GitHubService (`getInstallationUrl(state)`)
  - Добавить подробные логи в консоль для отладки
  - Вернуть JSON ответ с `redirectUrl` (вместо редиректа напрямую):
    ```json
    {
      "redirectUrl": "https://github.com/apps/..."
    }
    ```
    - Фронтенд (Garage) получает URL и выполняет `window.location.href = redirectUrl`
    - Это необходимо, так как при использовании `fetch` с `redirect: 'manual'` нельзя прочитать заголовок `Location` у кросс-доменных редиректов из-за CORS

**Тесты:**
- `api/test/integrations/github-routes.test.ts` или `api/test/routes/github.test.ts`
- Тесты для `/integration/github/connect`:
  - Успешное создание state и редирект на GitHub
  - Проверка прав доступа (только admin)
  - Обработка ошибок (проект не найден, пользователь не авторизован)

---

### 2.8. Создание HTTP endpoint для обработки GitHub callback

**Задача:** Реализовать endpoint для обработки callback от GitHub после установки App

**Файлы:**
- `api/src/integrations/github/routes.ts` (обновить существующий файл с роутами)

**Действия:**
- Добавить обработчик для endpoint `GET /callback` в `api/src/integrations/github/routes.ts` (полный путь: `/integration/github/callback`)
- Создать endpoint `GET /integration/github/callback?state=<state>&installation_id=<installation_id>`:
  - Принять `state` и `installation_id` от GitHub
  - **Проверить `state` (CSRF защита):**
    - **Если state это JWT:**
      - Проверить подпись JWT (валидация токена)
      - Проверить срок действия (`timestamp` не должен быть старше 15 минут)
      - Извлечь `projectId` и `userId` из payload JWT
      - Опционально: проверить, что `userId` соответствует текущему пользователю
    - **Если state это случайная строка:**
      - Найти `state` в Redis/сессии
      - Если не найден → вернуть ошибку (истек срок действия или поддельный state)
      - Извлечь `projectId` и `userId` из сохраненных данных
      - Удалить `state` из хранилища (одноразовое использование)
    - **Проверка CSRF:** Гарантирует, что callback пришел от GitHub для того же запроса подключения, который инициировал пользователь. Защищает от:
      - Подделки callback от злоумышленника
      - Повторного использования старых callback запросов
  - Использовать `installation_id` из параметров для сохранения конфигурации
  - Сохранить конфигурацию taskManager в проект:
    - `type: 'github'`
    - `config.installationId`
    - `config.repoId`
    - `config.repoFullName`
    - `connectedAt: Date`
    - `updatedAt: Date`
    - Сбросить `autoTaskEnabled: false` по умолчанию
  - Перенаправить на Garage: `/project/<projectId>/settings/task-manager?success=true`
  - В случае ошибки перенаправить с `?error=<errorMessage>`

**Тесты:**
- `api/test/integrations/github-routes.test.ts` (дополнить тесты для callback)
- Тесты для `/integration/github/callback`:
  - Успешный callback и сохранение конфигурации
  - Проверка валидации state (CSRF защита)
  - Обработка ошибок (неверный state, отсутствующий installation_id, GitHub API недоступен)
  - Редирект на Garage с параметрами успеха/ошибки

---

### 2.8.1. Создание HTTP endpoint для получения списка репозиториев

**Задача:** Реализовать endpoint для получения списка репозиториев, доступных для GitHub App installation

**Файлы:**
- `api/src/integrations/github/routes.ts` (обновить существующий файл с роутами)
- `api/src/integrations/github/service.ts` (добавить метод для получения списка репозиториев)

**Действия:**
- Добавить метод `getRepositoriesForInstallation(installationId: string): Promise<Repository[]>` в `GitHubService`:
  - Создать installation access token через `createInstallationToken(installationId)`
  - Использовать Octokit API `octokit.rest.apps.listReposAccessibleToInstallation()` для получения списка репозиториев
  - Вернуть массив репозиториев с полями: `id`, `name`, `full_name`, `private`, `html_url`
- Добавить обработчик для endpoint `GET /repositories` в `api/src/integrations/github/routes.ts` (полный путь: `/integration/github/repositories`):
  - Создать endpoint `GET /integration/github/repositories?projectId=<projectId>`:
    - Принять `projectId` из query параметров
    - Проверить права пользователя (только admin workspace может запрашивать репозитории)
    - Получить проект по `projectId` и проверить, что `taskManager` настроен
    - Извлечь `installationId` из `project.taskManager.config.installationId`
    - Вызвать `githubService.getRepositoriesForInstallation(installationId)`
    - Вернуть JSON ответ с массивом репозиториев:
      ```json
      {
        "repositories": [
          {
            "id": "123456",
            "name": "my-repo",
            "fullName": "owner/my-repo",
            "private": false,
            "htmlUrl": "https://github.com/owner/my-repo"
          }
        ]
      }
      ```
    - Это эфемерные данные, не сохраняются в базе
    - В случае ошибки вернуть соответствующий HTTP статус и сообщение об ошибке

**Тесты:**
- `api/test/integrations/github-routes.test.ts` (дополнить тесты)
- Тесты для `/integration/github/repositories`:
  - Успешное получение списка репозиториев
  - Проверка прав доступа (только admin)
  - Обработка ошибок (проект не найден, taskManager не настроен, GitHub API недоступен, installation не найдено)
  - Проверка, что возвращаются только репозитории для installation проекта

---

### 2.9. Создание Webhook endpoint для GitHub

**Задача:** Реализовать webhook endpoint для обработки событий от GitHub App

**Файлы:**
- `api/src/integrations/github/routes.ts` (обновить существующий файл с роутами)

**Действия:**
- Создать endpoint `POST /integration/github/webhook`:
  - Принять webhook payload от GitHub
  - Проверить подпись webhook используя `GITHUB_WEBHOOK_SECRET` (использовать `crypto.createHmac()`)
  - Обработать различные типы событий:
    - `installation.deleted` — удаление установки GitHub App:
      - Найти все проекты с `taskManager.config.installationId` равным удаленному installation ID
      - Удалить `taskManager` конфигурацию из этих проектов
      - Записать в лог информацию об удалении
    - Другие события (например, `installation.created`, `installation.suspend`, и т.д.):
      - Логировать событие для мониторинга
      - В будущем можно расширить обработку для других сценариев
  - Вернуть `200 OK` для успешной обработки
  - В случае ошибки валидации подписи вернуть `401 Unauthorized`
  - В случае других ошибок вернуть `500 Internal Server Error` и залогировать

**Примечание:** 
- Webhook secret используется GitHub для подписи payload с помощью HMAC SHA-256
- GitHub отправляет заголовок `X-Hub-Signature-256` с подписью в формате `sha256=<signature>`
- Необходимо проверить подпись перед обработкой webhook для безопасности

**Тесты:**
- Тесты для webhook endpoint можно добавить в `api/test/integrations/github-routes.test.ts` (вместе с другими тестами роутов)
- Тесты для валидации подписи:
  - Успешная валидация правильной подписи
  - Ошибка при неверной подписи
- Тесты для обработки событий:
  - `installation.deleted` — успешное удаление конфигурации
  - Обработка неизвестных типов событий (должны логироваться, но не вызывать ошибку)
- Тесты для обработки ошибок

---

### 2.10. Обновление типов TypeScript для Event

**Задача:** Добавить поле `taskManagerItem` в Event

**Файлы:**
- `types/src/dbScheme/groupedEvent.ts`

**Действия:**
- Добавить интерфейс `TaskManagerItem`:
  ```typescript
  interface TaskManagerItem {
    type: 'github-issue';
    number: number;
    url: string;
    title: string;
    createdBy: 'auto' | 'manual';
    createdAt: Date;
    assignee: 'copilot' | null;
  }
  ```
- Добавить поле `taskManagerItem?: TaskManagerItem` в `GroupedEventDBScheme`

**Тесты:** TypeScript компиляция

---

### 2.11. Обновление GraphQL схемы для Event

**Задача:** Добавить `taskManagerItem` в Event тип

**Файлы:**
- `api/src/typeDefs/event.ts`

**Действия:**
- Добавить тип `TaskManagerItem` в GraphQL схему
- Добавить поле `taskManagerItem: TaskManagerItem` в тип `Event`

---

### 2.12. Реализация мутаций для Event (createTaskForEvent, fixEventWithAgent)

**Статус:** Вторая итерация (см. раздел II)

**Задача:** Реализовать мутации для создания задач из событий

**Файлы:**
- `api/src/resolvers/event.js` (обновить существующий файл)

**Действия:**
- Реализовать `createTaskForEvent`:
  - Проверить, что `taskManagerItem` не существует
  - Получить проект и проверить наличие `taskManager`
  - Создать GitHub Issue через GitHubService
  - Сохранить `taskManagerItem` в Event с `createdBy: 'manual'`
  - Вернуть обновленный Event
- Реализовать `fixEventWithAgent`:
  - Если `taskManagerItem` не существует → создать Issue (manual)
  - Если `assignAgent === true` → попытаться назначить Copilot
  - Обновить `taskManagerItem.assignee = 'copilot'` при успехе
  - Вернуть обновленный Event

**Тесты:**
- `api/test/resolvers/event.test.ts` (дополнить существующие тесты)
- Тесты для `createTaskForEvent`:
  - Успешное создание задачи
  - Ошибка если задача уже существует
  - Ошибка если интеграция не настроена
- Тесты для `fixEventWithAgent`:
  - Создание задачи и назначение Copilot
  - Создание задачи без назначения (если Copilot недоступен)
  - Обновление существующей задачи

---

### 2.13. Форматирование GitHub Issue

**Задача:** Реализовать форматирование Issue для GitHub API

**Файлы:**
- В API: `api/src/integrations/github/` (если используется)
- В Worker: `workers/workers/task-manager/src/utils/issue.ts` (реализовано)

**Реализованный формат (см. `workers/workers/task-manager/src/utils/issue.ts`):**
- **Title:** `[Hawk] ${event.payload.title}`
- **Body:** (расширенный формат, отличается от первоначальной спецификации)
  - H2 заголовок с title
  - Stacktrace: первый фрейм с source code в diff-формате, остальные в `<details>`
  - Таблица: Since, Days Repeating, Total Occurrences, Users Affected
  - Context и Addons в `<details>` как JSON
  - Ссылка на Event в Hawk
  - Технический маркер: `<!-- hawk_groupHash: <groupHash> -->`
- **Labels:** `hawk:error`

**Тесты:**
- `api/test/integrations/github.test.ts` (дополнить)
- Тесты форматирования Issue с различными типами событий

---

### 2.14. Резолвер для taskManagerItem в Event

**Задача:** Добавить резолвер для поля `taskManagerItem` в Event (если требуется преобразование данных)

**Файлы:**
- `api/src/resolvers/event.js` (обновить существующий файл)

**Действия:**
- Если поле `taskManagerItem` читается напрямую из БД без преобразований — резолвер не требуется (GraphQL автоматически вернет значение)
- Если требуется преобразование данных (например, форматирование URL или преобразование типов) — добавить резолвер в `Event` type секцию

**Тесты:**
- Если резолвер добавлен, то дополнить тесты в `api/test/resolvers/event.test.ts`

---

### Фаза 3: Workers (Background Tasks)

### 3.1. Создание нового Worker: TaskManager

**Задача:** Создать worker для автоматического создания задач

**Файлы:**
- `workers/workers/task-manager/src/index.ts` (новый файл)
- `workers/workers/task-manager/package.json` (новый файл)
- `workers/workers/task-manager/types/task-manager-worker-task.ts` (новый файл)
- `workers/workers/task-manager/README.md` (новый файл)

**Действия:**
- Создать класс `TaskManagerWorker` наследуя от `Worker`.
- Определить тип worker: `hawk-worker-task-manager`
- Реализовать метод `handle(task: TaskManagerWorkerTask)`:
  - Получить все проекты с `taskManager.autoTaskEnabled === true`
  - Для каждого проекта:
    - Проверить daily budget (rate limiting)
    - Найти события без `taskManagerItem` с `totalCount >= threshold`
    - Создать задачи до исчерпания бюджета

**Тесты:**
- `workers/workers/task-manager/tests/index.test.ts`
- Тесты для обработки задач
- Тесты для rate limiting
- Тесты для фильтрации событий

---

### 3.2. Реализация алгоритма worker согласно спецификации

**Задача:** Реализовать алгоритм создания задач с учетом rate limiting

**Файлы:**
- `workers/workers/task-manager/src/index.ts`

**Действия:**
- Реализовать алгоритм:
  1. Выбрать проекты с `taskManager.type === 'github'` и `autoTaskEnabled === true`
  2. Для каждого проекта:
     - Вычислить `dayStartUtc` для "сегодня"
     - Проверить/сбросить `usage` если `dayStartUtc` отличается
     - Проверить `usage.autoTasksCreated >= MAX_AUTO_TASKS_PER_DAY`
     - Если бюджет доступен:
       - Атомарно инкрементировать `usage.autoTasksCreated`
       - Найти события:
         - `taskManagerItem` не существует
         - `timestamp >= connectedAt`
         - `totalCount >= taskThresholdTotalCount`
       - Для каждого события (до исчерпания бюджета):
         - Создать GitHub Issue
         - Сохранить `taskManagerItem` с `createdBy: 'auto'`
         - Назначить Copilot, если `assignAgent === true`
  3. Добавить логирование на всех этапах

**Константы:**
- `MAX_AUTO_TASKS_PER_DAY = 10` (или другое значение, можно вынести в env)

**Тесты:**
- `workers/workers/task-manager/tests/index.test.ts` (дополнить)
- Тесты для rate limiting логики
- Тесты для атомарного инкремента
- Тесты для фильтрации событий по времени и порогу

---

### 3.3. Интеграция с GitHub API из Worker

**Задача:** Использовать GitHub API для создания задач из worker

**Файлы:**
- `workers/workers/task-manager/src/GithubService.ts` (реализовано)
- `workers/workers/task-manager/src/index.ts`

**Действия:**
- Создать GitHubService, похожий на тот, что в api, но в workers. Только необходимые методы для создания задач.
- Использовать GitHubService для создания задач из worker

**Тесты:**
- Тесты для GitHubService
- Тесты обработки ошибок при создании Issue

---

### 3.4. Атомарный инкремент usage для rate limiting

**Задача:** Реализовать атомарное обновление usage для rate limiting

**Файлы:**
- `workers/workers/task-manager/src/index.ts` (реализовано внутри worker, не отдельный сервис)

**Реализация:**
- Функция атомарного инкремента реализована **прямо в worker**, не в отдельном сервисе
- Логика: MongoDB `findOneAndUpdate` с условием проверки бюджета

---

### 3.5. Настройка Cron Manager и RabbitMQ для запуска TaskManager worker

**Задача:** Настроить расписание и биндинги для автоматического создания задач

**Файлы:**
- `cron-manager/config.yml` (или аналог)

**Действия:**
1. Добавить задачу в конфигурацию cron-manager:
   ```yaml
   tasks:
     - schedule: "0 * * * *"  # Каждый час
       routingKey: "cron-tasks/task-manager"
       payload:
         type: "auto-task-creation"
   ```

2. **Обязательно:** Добавить биндинги в RabbitMQ:
   - Открыть RabbitMQ Management UI (обычно http://localhost:15672)
   - **Exchanges** → `cron-tasks` → **Bindings**
   - **Add binding from this exchange**:
     - **Routing key:** `cron-tasks/task-manager`
     - **To queue:** `cron-tasks/task-manager`
   - Без этого биндинга сообщения от cron-manager не дойдут до worker

**Примечание:** Расписание можно сделать настраиваемым через env переменную.

**Тесты:** Не требуется (конфигурация)

---

### 3.6. Обновление типов для Worker Task

**Задача:** Определить тип задачи для TaskManager worker

**Файлы:**
- `workers/workers/task-manager/types/task-manager-worker-task.ts`

**Действия:**
- Определить интерфейс:
  ```typescript
  interface TaskManagerWorkerTask extends WorkerTask {
    type: 'auto-task-creation';
  }
  ```

**Тесты:** TypeScript компиляция

---

### 3.7. Обработка ошибок в Worker

**Задача:** Обработать ошибки при создании задач

**Файлы:**
- `workers/workers/task-manager/src/index.ts`

**Действия:**
- Обработать ошибки:
  - GitHub API недоступен → логировать и продолжить
  - Репозиторий не найден → логировать и пропустить проект
  - Права недостаточны → логировать и пропустить проект
  - Rate limit GitHub → логировать и продолжить на следующем запуске
- Использовать `NonCriticalError` для некритичных ошибок
- Использовать `CriticalError` для критичных ошибок

**Тесты:**
- Тесты обработки различных типов ошибок
- Тесты логирования ошибок

---

### 3.8. Добавление worker в список доступных workers

**Задача:** Зарегистрировать новый worker

**Файлы:**
- `workers/package.json` (добавить в workspaces)
- `workers/runner.ts` (если нужно)
- `workers/lib/workerNames.ts` (если есть)

**Действия:**
- Добавить worker в workspaces
- Добавить скрипт для запуска: `run-task-manager`
- Обновить документацию

**Тесты:** Запуск worker вручную

---

### Дополнительные задачи

### 4.1. Добавление переменных окружения

**Задача:** Документировать и добавить все необходимые переменные окружения

**Файлы:**
- `.env.sample` в корне проекта
- `api/.env.sample`
- `workers/.env.sample`

**Действия:**
- Добавить переменные для GitHub App
- Добавить `MAX_AUTO_TASKS_PER_DAY` для workers
- Добавить GitHub OAuth callback URLs

---

### 4.2. Обновление документации

**Задача:** Обновить README и другую документацию

**Файлы:**
- `docs/task-managers-create-github-app.md`

**Действия:**
- Добавить инструкции по настройке GitHub App

---

## II. SECOND ITERATION

Задачи для следующей итерации после MVP.

---

### II.1. Кнопки "Create an Issue" и "Fix with Copilot" на странице Event (Garage)

**Связь с MVP:** 1.7

**Задача:** Добавить ручное создание задач и назначение Copilot

**Файлы:**
- `garage/src/components/.../EventHeader.vue`

**Действия:**
- Если задачи нет → показать кнопку "Create an Issue"
- Если интеграция подключена → показать кнопку "Fix with Copilot"
- Кнопки в блоке `event-header__buttons` по правому краю

---

### II.2. Мутации createTaskForEvent и fixEventWithAgent (Garage + API)

**Связь с MVP:** 1.8, 2.11, 2.12

**Задача:** Реализовать создание задач вручную и назначение Copilot из UI

**Файлы:**
- `garage/src/api/` — добавить вызовы мутаций
- `api/src/typeDefs/event.ts` — input типы `CreateTaskForEventInput`, `FixEventWithAgentInput`
- `api/src/resolvers/event.js` — резолверы `createTaskForEvent`, `fixEventWithAgent`

**Действия:**
- Добавить мутации в Garage
- Реализовать резолверы в API (см. раздел 2.12)

---

### II.3. Вынос GitHubService в @hawk.so/utils

**Связь с MVP:** 3.3

**Задача:** Устранить дублирование GitHubService между API и Workers

**Действия:**
- Создать пакет `@hawk.so/utils` (если ещё не существует)
- Вынести общую логику GitHubService в пакет
- Обновить API и Workers для использования общего сервиса

---

### II.4. Улучшения выбора репозитория (Garage + API)

**Связь с MVP:** 1.3, endpoint списка репозиториев

**Задача:** Улучшить UX компонента выбора репозитория

**Файлы:**
- `api/src/integrations/github/` — endpoint или метод `getRepositoriesForInstallation`
- `garage/src/components/project/settings/TaskManagerIntegration.vue`

**Действия:**
- Отсортировать список репозиториев по алфавиту на стороне API (по `fullName` или `name`)
- Добавить поддержку большего числа иконок репозиториев (GitHub возвращает `language` — использовать для отображения иконок языков программирования)
- Попробовать заменить CustomSelect на CodeX Ui: Popover + Context Menu для лучшего UX при большом количестве репозиториев

---

## Порядок выполнения

Рекомендуемый порядок реализации:

1. **GitHub App настройка (2.1)** — сделать в первую очередь, чтобы иметь доступ к API
2. **Garage: Типы, GraphQL и локализация (1.8, 1.9, 1.10)** — подготовка инфраструктуры
3. **API: Типы и схема (2.4, 2.5)** — базовая структура данных
4. **API: GitHub Service (2.3)** — сервис для работы с GitHub
5. **API: HTTP endpoint connect (2.7)** — endpoint для инициации подключения (`/integration/github/connect`)
6. **API: HTTP endpoint callback (2.8)** — endpoint для обработки callback от GitHub (`/integration/github/callback`)
7. **API: Webhook endpoint (2.9)** — обработка webhook событий от GitHub (удаление установки)
8. **API: Резолверы Project (2.6)** — настройка интеграции (disconnect и update settings)
9. **Garage: UI настройки и локализация (1.1-1.6, 1.10)** — интерфейс настройки (редирект на `/integration/github/connect` вместо прямого GitHub URL) и переводы
10. **API: Event мутации (2.12, 2.13)** — создание задач вручную
11. **Garage: UI Event (1.7)** — интерфейс на странице события
12. **Worker: TaskManager (3.1-3.8)** — автоматическое создание задач

После каждого пункта пишутся и выполняются соответствующие тесты.

---

## Критерии готовности

**MVP (реализовано):**
- ✅ GitHub App создан и настроен
- ✅ Garage: UI для настройки интеграции работает
- ✅ Garage: Запрос списка репозиториев и выбор репозитория после установки App
- ✅ Garage: Отображение "Issue #N" на странице события (если задача существует)
- ✅ API: Мутации `disconnectTaskManager`, `updateTaskManagerSettings` работают
- ✅ Worker: Автоматическое создание задач работает по расписанию
- ✅ Webhook: Обработка `installation.deleted`

**Вторая итерация (раздел II):**
- Кнопки "Create an Issue" и "Fix with Copilot"
- Мутации `createTaskForEvent` и `fixEventWithAgent`
- Улучшения выбора репозитория (сортировка, иконки, CodeX Ui Popover + Context Menu)
