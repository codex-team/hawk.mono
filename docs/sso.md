# Hawk SSO (Single Sign-On) — Specification

## 1. Цели и границы

### 1.1 Цель

Добавить поддержку корпоративного SSO в Hawk для enterprise-клиентов, начиная с **AD FS (SAML 2.0)**, с возможностью расширения на **Keycloak** и **OIDC** в будущем.

### 1.2 Не входит в MVP

- SCIM / автоматическая синхронизация пользователей
- SAML Single Logout (SLO)
- Группы / роли из IdP
- OIDC (будет следующим этапом)

---

## 2. Термины и сокращения

### SSO (Single Sign-On)

Механизм, при котором пользователь аутентифицируется один раз у внешнего провайдера идентификации (IdP), а затем получает доступ к Hawk без ввода логина и пароля.

### IdP (Identity Provider)

Внешняя система аутентификации пользователей (например, **AD FS**, **Keycloak**), которая подтверждает личность пользователя и возвращает Hawk информацию о нём.

### SP (Service Provider)

Приложение, которое доверяет IdP и принимает результат аутентификации. В контексте этой спецификации SP — это Hawk.

### SAML (Security Assertion Markup Language)

Корпоративный стандарт SSO на основе XML и цифровых подписей. Широко используется в enterprise-инфраструктурах и поддерживается AD FS. Hawk выступает в роли SAML Service Provider.

### OIDC (OpenID Connect)

Современный протокол аутентификации поверх OAuth 2.0. Проще в реализации и отладке, хорошо поддерживается Keycloak. Планируется для будущего расширения.

### SCIM (System for Cross-domain Identity Management)

Протокол для автоматической синхронизации пользователей и групп между IdP и приложением (создание, блокировка, удаление пользователей). Не входит в MVP.

---

## 3. Общий флоу настройки и использования SSO

Краткая схема работы SSO в Hawk:

0. В конфиг Hawk API добавляется
    - `SSO_SP_ENTITY_ID` — уникальное имя хоука для IdP провайдеров. Например `urn:hawk:tracker:saml`;

1. **Администратор Workspace**

   - получает SAML-параметры у своей IT-службы или администратора IdP (AD FS / Keycloak);
        - мы передаем администратору 
            - `SSO_SP_ENTITY_ID`
            - `ACS endpoint (Assertion Consumer Service URL)`. Вида `https://api.hawk.so/auth/sso/saml/{workspaceId}/acs`
        - Администратор IdP (AD FS) создаёт `Relying Party Trust`
            - `Relying Party Identifier` = `SSO_SP_ENTITY_ID`
            - `Assertion Consumer Service URL` = `ACS endpoint`
            - после создания будут получены метаданные, которые надо будет ввести в Хоуке в Настройках Воркспейса
   - типовой набор данных:
     - IdP Entity ID;
     - SSO URL;
     - публичный X.509 сертификат;
     - имена атрибутов (email, имя);
     - при необходимости — формат NameID.

2. Администратор открывает настройки Workspace в Hawk и:

   - включает SSO;
   - заполняет SAML-параметры;
   - сохраняет конфигурацию.

3. Hawk сохраняет конфигурацию в `workspaces.sso`.

4. **Пользователь** открывает страницу авторизации с Deep Link вида https://garage.hawk.so/login/<workspaceId>
    - Адрес этой страницы раздает сотрудникам администратор Identity Provider
    - Она должна быть скрыта от поисковиков
    - Как фоллбэк, на обычную страницу логина можно добавить кнопку «Continue with SSO», которая открывает форму для ввода `workspaceId`
    - `workspaceId` может быть заменен на `workspace.slug` (когда такая фича появится в Хоуке)

5. Фронтенд Hawk инициирует SSO-вход, перенаправляя браузер в Hawk API на sso-initiation адрес (см 5.2.1) с передачей `RelayState` в параметрах

   - `redirect to https://api.hawk.so/auth/sso/saml/:workspaceId?returnUrl=/workspace/<id>`.

6. Бэкенд Hawk:

    - формирует `SAML AuthnRequest`;
    - сохраняет `RelayState` (контекст возврата пользователя);
        - читает `returnUrl`
	    - сохраняет его во временное хранилище (cookie / in-memory / redis)
	    - кладёт идентификатор этого состояния в `RelayState`
    - перенаправляет браузер пользователя на страницу логина IdP.

7. Пользователь аутентифицируется в IdP (пароль, MFA и т.д.).

8. IdP возвращает браузер пользователя обратно в Hawk (ACS callback) с `SAMLResponse`.

9. Бэкенд Hawk:

    - валидирует `SAML Response`;
    - разобирает `Assertion`
    - извлекает `NameID`
    - идентифицирует пользователя по `NameID`;
        - ищет users.identities[workspaceId].saml.id
	- если нашли — логиним
	- если нет — применяем политику доступа (invite / JIT)
    - создаёт сессию Hawk

10. Пользователь перенаправляется в интерфейс Hawk (на страницу из `RelayState`).

---

## 3.1 Общая модель SSO в Hawk

### 3.1 Уровень SSO

SSO настраивается **на уровне workspace**.

Один пользователь может:

- состоять в нескольких workspace;
- использовать SSO в одном workspace;
- использовать email/password в другом workspace.

SSO не является глобальной настройкой аккаунта пользователя.

---

## 4. Хранилище данных (MongoDB)

### 4.1 Workspace

В коллекцию `workspaces` добавляется опциональное поле `sso`.

```js
workspaces: {
  _id: "66a...",
  name: "Frontend [production]",
  tariff: "TEAM",
  isBlocked: false,
  ...

  sso: {
    enabled: true,
    enforced: false,
    type: "saml",

    saml: {
      // идентификатор IdP, который клиент присылает вам в метаданных
      idpEntityId: "https://adfs.company.com/adfs/services/trust",

      // куда редиректить пользователя для логина
      ssoUrl: "https://adfs.company.com/adfs/ls/",

      // публичный сертификат IdP в PEM (для проверки подписи SAMLResponse)
      x509Cert: "-----BEGIN CERTIFICATE-----
MIIC...
-----END CERTIFICATE-----",

      // желаемый формат NameID
      nameIdFormat: "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",

      // как искать нужные атрибуты в Assertion
      attributeMapping: {
        email: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        name: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
      }
    }
  }
}
```

#### Описание полей `workspaces.sso`

- **enabled** — включает или выключает SSO для workspace.
- **enforced** — если `true`, вход в этот workspace возможен только через SSO; вход по email/password запрещён.
- **type** — тип провайдера (`saml` для MVP).

#### Описание полей `workspaces.sso.saml`

- **idpEntityId** — уникальный идентификатор IdP (из SAML-метаданных IdP).
  - **Зачем:** Hawk использует на этапе 9 Флоу для валидации ответа, чтобы убедиться, что пришедший `SAMLResponse` относится именно к ожидаемому провайдеру и конфигурации.
  - На практике это участвует в проверках "этот ответ предназначен Hawk" (см. [5.2.2](#acs-callback)).

    Внутри `SAMLResponse` есть блок `Assertion`, в котором есть поле `Audience`. Упрощенно:

    ```xml
    <Audience>urn:hawk:tracker:saml</Audience>
    ```
    что означает «Я подтверждаю личность пользователя **для вот этого приложения**»
    Без этой проверки было бы возможно принять SAMLResponse, от другого IdP, от другой конфигурации, предназначенный для другого приложения.

- **ssoUrl** — URL IdP, на который Hawk перенаправляет пользователя для аутентификации.

- **x509Cert** — публичный X.509 сертификат IdP, используемый Hawk для проверки цифровой подписи SAML Response.

- **nameIdFormat** — формат значения `NameID`, которое IdP будет помещать в SAML Assertion.
  - Пример (email-формат): `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress` — тогда `NameID` выглядит как `alice@company.com`.
  - Пример (persistent identifier): `urn:oasis:names:tc:SAML:2.0:nameid-format:persistent` — тогда `NameID` выглядит как стабильный идентификатор вида `f2a7c1c8-7b6a-4c5a-9c2d-...` (не меняется при смене email).
  - Это константа (enum) из спецификации SAML
  - Формально: 
    - urn: — Uniform Resource Name, 
    - oasis — организация, которая стандартизирует SAML
    - SAML:1.1:nameid-format:emailAddress — конкретный формат идентификатора
  - IdP (AD FS / Keycloak) понимает эту строку
  - Hawk передаёт её в AuthnRequest как пожелание: «пришли мне NameID в таком формате»

- **attributeMapping** — сопоставление атрибутов из SAML Assertion с полями Hawk.
  - **Зачем:** разные IdP/инсталляции отдают email/имя под разными именами claim’ов.
  - Пример для AD FS:
    - `email: "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"`
    - `name:  "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"`
        - Это claim identifiers
        - Microsoft (AD / ADFS) использует URI-подобные строки как имена атрибутов
        - Пример SAML Assertion (упрощённо):

        ```xml
        <Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress">
            <AttributeValue>alice@company.com</AttributeValue>
        </Attribute>
        ```
        - значит "при разборе XML найти `<Attribute>` с соответствующим `Name`, взять его значение и положить в `user.email`"
  - Пример для Keycloak (часто):
    - `email: "email"`
    - `name:  "given_name"` или `"name"`

Поле `sso`:

- присутствует только у workspace с включённым SSO;
- не возвращается в обычных GraphQL-запросах;
- доступно только администраторам workspace.

---

### 4.2 User identities

В коллекции `users` хранится информация о внешних идентичностях пользователя.

```js
users: {
  _id,
  email,
  passwordHash,
  workspaces: { ... },

  identities?: {
    "<workspaceId>": {
      saml: {
        id: string,
        email: string
      }
    }
  }
}
```

#### Что такое `identities`

`identities` — это связь между пользователем Hawk и его учётной записью во внешнем IdP **в контексте конкретного Workspace**.

- ключ верхнего уровня — `workspaceId`
- внутри хранится информация о том, как пользователь идентифицируется в IdP

#### Поля `saml`

- **id** — уникальный идентификатор пользователя в IdP (значение `NameID` из SAML Assertion). Это стабильный идентификатор, не зависящий от email.
- **email** — email пользователя на момент первичной привязки (для аудита и диагностики).

---

## 5. Аутентификация и API

### 5.1 GraphQL

- GraphQL API не используется для коммуникации с IdP
- Используется для внутренних операций в Хоуке: 
    - обновить настройки `sso` воркспейса

---

### 5.2 HTTP endpoints для SAML

SAML использует отдельные HTTP endpoints, так как IdP не умеет работать с GraphQL.

---

#### 5.2.1 Инициация входа (SSO Login Initiation)

```
GET /auth/sso/saml/:workspaceId?redirectUrl=/workspace/<worspaceId>
```

**Что это:** Начальная точка SSO-аутентификации. Этот endpoint запускает процесс SAML-входа и в итоге приводит пользователя на страницу логина IdP.

Endpoint должен вызываться как переход браузера (navigation, а не аякс-запрос), чтобы HTTP 302 реально отправил пользователя на `ssoUrl IdP`.

**Кто и когда инициирует:**

- **Инициатор — браузер пользователя**, по действию во фронтенде Hawk.
- Типовой момент вызова: пользователь приходит по ссылке вида `/login/<workspaceId>` или на странице логина нажимает кнопку **«Continue with SSO»**, вводя после этого `workspaceId` (или `slug`).

**Что такое RelayState:** `RelayState` — термин из SAML-протокола. Это параметр, который **бэкенд Hawk** передаёт IdP вместе с SAML AuthnRequest и затем получает обратно на ACS endpoint.

В контексте Hawk:

- **инициатор** — фронтенд Hawk (действие пользователя);
- **формирует и сохраняет RelayState** — бэкенд Hawk;
- **возвращает RelayState обратно** — IdP;
- **использует RelayState** — бэкенд Hawk.

Зачем он нужен:

- сохранить контекст входа (например, куда вернуть пользователя после SSO: конкретный проект, страницу или workspace).

Обычно RelayState содержит либо:

- `returnUrl` (если разрешено), либо
- короткий идентификатор состояния, по которому Hawk на сервере находит сохранённые данные.

Пример адреса, на который фронтендом Hawk редиректит пользователя при начале SSO-логина:

```
https://api.hawk.so/auth/sso/saml/:workspaceId?returnUrl=/workspace/<id>
```

В этом случае:

- фронтенд Hawk передаёт `returnUrl` в урле;
- бэкенд Hawk сохраняет его как RelayState;
- после успешного SSO пользователь будет возвращён на `/workspace/<workspaceId>`.
- Обычно это `returnUrl` или короткий идентификатор состояния, который Hawk сопоставляет с сохранёнными данными (чтобы не хранить длинный URL в открытую).

**Что делает endpoint:**

1. Проверяет, что `workspaces.sso.enabled = true`.
2. Формирует SAML AuthnRequest (запрос аутентификации).
3. Сохраняет `RelayState` (куда вернуть пользователя после логина).
4. Перенаправляет браузер пользователя на `ssoUrl` IdP.

---

#### <a name="acs-callback"></a>5.2.2 ACS callback (Assertion Consumer Service)

```
POST /auth/sso/saml/:workspaceId/acs
```

**Что это:** Endpoint, который принимает результат аутентификации от IdP.

**Что делает endpoint:**

1. Принимает `SAMLResponse` (form POST).
    - Content-Type: application/x-www-form-urlencoded
    - В теле запроса:
    ```
    SAMLResponse=<base64-encoded XML>
    RelayState=<optional>
    ```

2. Валидирует:
   - цифровую подпись (через `x509Cert`);
        - Зачем: убедиться, что ответ действительно подписан IdP, которому мы доверяем, и не был изменён.
        - Как технически
            - В XML SAML Response есть блок:

            ```xml
            <ds:Signature>...</ds:Signature>
            ```
            - Хоук извлекает подпись
            - берёт публичный сертификат из базы - `workspaces.sso.saml.x509Cert`;
	        - криптографически проверяет подпись XML
            - если подпись невалидна или подписано другим ключом — отказ (SSO login failed)
        - Реализация через SAML-библиотеку (@node-saml/node-saml)

   - `Audience` 
        - Это защита от ситуации: “Этот ответ был выдан не для Hawk”
        - Внутри Assertion есть:
        ```xml
        <Audience>urn:hawk:tracker:saml</Audience>
        ```
        - Hawk знает свой `SSO_SP_ENTITY_ID` (из .env).
        - сравнивает `Audience === SSO_SP_ENTITY_ID`. 
        - Если не совпало → ответ отклоняется.
   - `Recipient`
        - Это URL, куда IdP ожидал отправить ответ:
        ```xml
        <SubjectConfirmationData Recipient="https://api.hawk.so/auth/sso/saml/{workspaceId}/acs" />
        ```

        - Hawk знает свой URL ACS endpoint (из роутов)
        - сравнивает `Recipient === ACS_URL`.
        - Если не совпало → ответ отклоняется.
   - `InResponseTo`;
        - Зачем: защита от replay-атак.
        - На этапе `GET /auth/sso/saml/:workspaceId` Hawk генерирует `AuthnRequest`, у которого есть уникальный ID, например 
        ```
        _a8f7c3...
        ```
        - Hawk API сохраняет этот ID (в сессии / кеше)
        - В `SAMLResponse` есть:
        ```
        InResponseTo="_a8f7c3..."
        ```
        - Hawk проверяет что 
            - такой `AuthnRequest` реально был
            - он ещё не использован
            - он относится к этому workspace
        - Если `InResponseTo` неизвестен или уже использован — отказ
   - временные ограничения Assertion.
        - В Assertion есть:
        ```xml
        <Conditions NotBefore="2025-03-01T10:00:00Z"
            NotOnOrAfter="2025-03-01T10:05:00Z" />
        ```
        - На основе текущего серверного времени Хоук проверяет
        ```
        now >= NotBefore
        now < NotOnOrAfter
        ```
        - учитывает небольшой clock skew (обычно ±2–5 минут).
        - Если Assertion просрочена или ещё “не действительна” — отказ

3. Извлекает из XML :
   - `NameID` → `users.identities[workspaceId].saml.id`;
        - пример в xml
        ```xml
        <Subject>
            <NameID>alice@company.com</NameID>
        </Subject>
        ```
        - Это основной идентификатор пользователя для SSO
   - email пользователя.
        - пример в xml 
        ```xml
        <Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress">
            <AttributeValue>alice@company.com</AttributeValue>
        </Attribute>
        ```
        - Hawk:
	        - берёт `attributeMapping.email` из `workspaces.sso`;
	        - ищет `Attribute` с таким `Name`;
	        - берёт его значение;
	        - использует как `email`.
        - Если email отсутствует или не найден по mapping:
            - либо отказ,
            - либо логика fallback (решается политикой).

4. Находит по (workspaceId, saml.id) или создаёт пользователя Hawk.
5. Проверяет политику доступа workspace.
    - invite-only / JIT
	- enforced SSO
6. Создаёт сессию Hawk.
7. Перенаправляет пользователя в web-app
    - используя RelayState
    - 302

CSRF-проверка не применяется — безопасность обеспечивается криптографией SAML.

---

## 6. Политика доступа и provisioning пользователей

### 6.1 Provisioning пользователей

Provisioning — это процесс определения, **может ли пользователь получить доступ к workspace** после успешной аутентификации в IdP.

SSO подтверждает личность пользователя, но не гарантирует, что он имеет право доступа к workspace.

### 6.2 Политика доступа пользователя

В MVP используется одна из политик (выбирается заранее):

- **Только приглашённые** — пользователь должен уже быть членом workspace.
- **Автоматическое добавление (JIT provisioning)** — пользователь добавляется в workspace при первом успешном SSO-входе.

**JIT** = *Just-In-Time*.

Политика применяется после успешной SAML-аутентификации.

---

## 7. Enforcement (SSO Required)

Если `workspaces.sso.enforced = true`:

- вход по email/password в этот workspace запрещён;
- SSO является единственным способом входа;
- другие workspace пользователя не затрагиваются.

---

## 8. Web UI

### 8.1 Login flow

- пользователь переходит на страницу логина Workspace (заранее зная ее адрес вида `/login/sso/<workspaceId>`) или перейдя по кнопке "Continue with SSO" и введя `workspaceId` (или `slug`)
- Hawk проверяет наличие `sso.enabled`;
- если SSO включён — редирект в API.

---

### 8.2 Настройки workspace (admin only)

**Что это:** Экран настройки SSO для администраторов workspace.

**Процесс:**

1. Администратор получает параметры SAML у своей IT-службы / IdP:
   - IdP Entity ID
   - SSO URL
   - X.509 сертификат
2. Администратор вводит эти данные в UI Hawk.
3. Фронтенд вызывает GraphQL-мутацию обновления workspace.
4. Hawk сохраняет конфигурацию в `workspaces.sso`.
5. Администратор может включить `enabled` и `enforced`.

---

## 9. Безопасность

### 9.1 Идентификация пользователя

На практике это означает:

- Hawk связывает пользователя с IdP **по стабильному идентификатору**.
  - В SAML внутри `SAMLResponse` есть Assertion, в которой есть поле `NameID` — это и есть идентификатор пользователя в IdP для данного приложения.
  - Hawk сохраняет его в `users.identities[workspaceId].saml.id` и при каждом следующем SSO-входе ищет пользователя по этой паре `(workspaceId, saml.id)`.
- email используется как атрибут, но не как идентификатор входа;
- смена email в IdP не приводит к потере доступа.

### 9.2 Email не является primary identifier

Это означает:

- Hawk не использует email для поиска пользователя при SSO-входе;
- совпадение email без совпадения `NameID` не считается тем же пользователем;
- это защищает от подмены аккаунта.

### 9.3 Ограничение доступа к SAML-конфигурации

Для этого необходимо:

- **Разделить публичную и админскую модель workspace** в GraphQL (например, разные поля/типы или разные резолверы).
- В стандартных query (например, `workspace`, `myWorkspaces`) **не резолвить поле `sso` вообще**.
- Сделать отдельный admin-only query/mutation (например, `workspaceSsoSettings(workspaceId)`), который:
  - проверяет права администратора workspace;
  - возвращает/изменяет `workspaces.sso`.

Технически это означает:

- в резолверах GraphQL не выбирать `sso` по умолчанию (projection/DTO), либо вычищать его перед возвратом;
- добавить guard `isAdmin` на резолвер, который отдаёт `sso`.

### 9.4 Аудит и логирование SSO

- ошибки SSO логируются на уровне backend API;
- логируются тип ошибки и workspaceId (без хранения SAML Assertion целиком);
- логирование используется для диагностики и поддержки клиентов.

### 9.5 Разлогин пользователя в Хоуке при удалении его у IdP

Hawk не выполняет онлайн-проверку статуса пользователя в IdP для каждой сессии.
Вместо этого мы уменьшим время жизни сесси при SSO с 30 дней до 2 дней.
Если пользователь был удалён или заблокирован в IdP, следующий SSO-вход будет отклонён IdP, и Hawk не создаст новую сессию.

---

## 10. Тестирование

### 10.1 Unit tests

Располагаются в API-сервисе.

Покрывают:

- парсинг и валидацию SAML Response;
- attribute mapping;
- linking `users.identities`;
- политику доступа и enforcement.

---

### 10.2 Integration tests

- Keycloak (SAML) в Docker;
- e2e сценарий: login → callback → session.

---

### 10.3 Manual tests

- реальный AD FS (staging или клиентский стенд);
- проверка claim rules и сертификатов.

---

## 11. Будущее расширение

- вынесение IdP в отдельную коллекцию;
- поддержка OIDC;
- SCIM;
- группы и роли из IdP.

