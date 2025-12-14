# План имплементации SSO (Single Sign-On) для Hawk

## Обзор

Этот документ описывает пошаговый план имплементации SSO функциональности согласно спецификации `docs/sso.md`. План разбит на этапы с конкретными задачами для разработчика.

**Технологии:**
- API: Node.js, Express, GraphQL (Apollo Server), MongoDB
- Frontend: Vue 3, Vuex, Vue Router
- SAML библиотека: `@node-saml/node-saml`

**Подход:** TDD для критичных частей (SAML endpoints), тесты по ходу разработки.

---

## Этап 1: Подготовка окружения и зависимостей

### 1.1 Установка зависимостей

**Файл:** [`api/package.json`](../api/package.json)

**Действия:**
1. Добавить зависимость `@node-saml/node-saml` в `dependencies`
2. Добавить типы `@types/node-saml` в `devDependencies` (если доступны)
3. Выполнить `yarn install`

### 1.2 Обновление env переменных

**Файл:** [`api/src/types/env.d.ts`](../api/src/types/env.d.ts)

**Действия:**
1. Добавить типы для новых env переменных:
   - `SSO_SP_ENTITY_ID` — уникальный идентификатор SP (например, `urn:hawk:tracker:saml`)
   - `GARAGE_URL` — URL фронтенда (уже может быть, проверить)

**Код:**
```typescript
declare namespace NodeJS {
  export interface ProcessEnv {
    // ... существующие переменные
    
    /**
     * SSO Service Provider Entity ID
     * Unique identifier for Hawk in SAML IdP configuration
     */
    SSO_SP_ENTITY_ID: string;
    
    /**
     * Frontend application URL
     */
    GARAGE_URL: string;
  }
}
```

**Файл:** [`api/.env.sample`](../api/.env.sample) (создать если нет, или обновить существующий)

**Действия:**
1. Добавить примеры значений для новых переменных. С описанием.

**Код:**
```
SSO_SP_ENTITY_ID=urn:hawk:tracker:saml
GARAGE_URL=http://localhost:8080
```

---

## Этап 2: Создание структуры SSO модуля в API

### 2.1 Создание директории и базовых файлов

**Структура:**
```
api/src/sso/
  ├── index.ts              # Главный экспорт модуля
  ├── saml/
  │   ├── index.ts          # SAML роутер
  │   ├── controller.ts     # Обработчики SAML endpoints
  │   ├── service.ts        # Бизнес-логика SAML
  │   ├── types.ts          # TypeScript типы для SAML
  │   └── utils.ts          # Утилиты (парсинг, валидация)
  └── types.ts              # Общие типы SSO
```

**Действия:**
1. Создать директорию `api/src/sso/`
2. Создать поддиректорию `api/src/sso/saml/`
3. Создать пустые файлы для будущей реализации

### 2.2 Создание типов для SSO

**Файл:** [`api/src/sso/types.ts`](../api/src/sso/types.ts)

**Действия:**
1. Определить TypeScript интерфейсы для SSO конфигурации:
   - `WorkspaceSsoConfig` — общая конфигурация SSO
   - `SamlConfig` — SAML-специфичная конфигурация
   - `SamlAttributeMapping` — маппинг атрибутов
   - `SamlResponseData` — данные из SAML Response

**Код:**
```typescript
/**
 * SAML attribute mapping configuration
 */
export interface SamlAttributeMapping {
  /**
   * Attribute name for email in SAML Assertion
   * 
   * @example "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress" 
   * to get email from XML like this:
   *  <Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress">
   *    <AttributeValue>alice@company.com</AttributeValue>
   *  </Attribute>
   */
  email: string;
  
  /**
   * Attribute name for user name in SAML Assertion
   */
  name?: string;
}

/**
 * SAML SSO configuration
 */
export interface SamlConfig {
  /**
   * IdP Entity ID.
   * Used to validate "this response is intended for Hawk"
   * @example "urn:hawk:tracker:saml"
   */
  idpEntityId: string;
  
  /**
   * SSO URL for redirecting user to IdP
   * Used to redirect user to IdP for authentication
   * @example "https://idp.example.com/sso"
   */
  ssoUrl: string;
  
  /**
   * X.509 certificate for signature verification
   * @example "-----BEGIN CERTIFICATE-----\nMIIDYjCCAkqgAwIBAgI...END CERTIFICATE-----"
   */
  x509Cert: string;
  
  /**
   * Desired NameID format
   * @example "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
   */
  nameIdFormat?: string;
  
  /**
   * Attribute mapping configuration
   * Used to extract user attributes from SAML Response
   */
  attributeMapping: SamlAttributeMapping;
}

/**
 * SSO configuration for workspace
 */
export interface WorkspaceSsoConfig {
  /**
   * Is SSO enabled
   */
  enabled: boolean;
  
  /**
   * Is SSO enforced (only SSO login allowed)
   * If true, login via email/password is not allowed
   */
  enforced: boolean;
  
  /**
   * SSO provider type
   * Currently only SAML is supported. In future we can add other providers (OAuth 2, etc.)
   */
  type: 'saml';
  
  /**
   * SAML-specific configuration.
   * Got from IdP metadata.
   */
  saml: SamlConfig;
}

/**
 * Data extracted from SAML Response
 */
export interface SamlResponseData {
  /**
   * NameID value (user identifier in IdP)
   */
  nameId: string;
  
  /**
   * User email
   */
  email: string;
  
  /**
   * User name (optional)
   */
  name?: string;
  
  /**
   * Identifier that should match AuthnRequest ID
   * 
   * @example "_a8f7c3..."
   */
  inResponseTo?: string;
}
```

**Файл:** [api/src/sso/saml/types.ts](../api/src/sso/saml/types.ts)

**Действия:**
1. Определить внутренние типы для работы SAML модуля (не экспортируются наружу):
   - Типы для промежуточных данных при парсинге SAML Response
   - Типы для ошибок валидации SAML
   - Типы для работы с библиотекой `@node-saml/node-saml` (если нужны обёртки)

**Примечание:** Основные SAML типы (`SamlConfig`, `SamlAttributeMapping`, `SamlResponseData`) уже определены в `api/src/sso/types.ts`, так как они используются в общем интерфейсе `WorkspaceSsoConfig` и экспортируются наружу. Файл `saml/types.ts` предназначен для внутренних типов, используемых только внутри SAML модуля.

---

## Этап 3: Обновление моделей данных

### 3.1 Обновление типов Workspace

**Файл:** [`types/src/dbScheme/workspace.ts`](../types/src/dbScheme/workspace.ts)

**Действия:**
1. Добавить опциональное поле `sso` в интерфейс `WorkspaceDBScheme`
2. Использовать типы из `api/src/sso/types.ts` (или вынести в общий пакет [@hawk.so/types](../types/))

**Код:**
```typescript
import { WorkspaceSsoConfig } from '../../api/src/sso/types'; // или из общего пакета

export interface WorkspaceDBScheme {
  // ... существующие поля
  
  /**
   * SSO configuration (optional, only for workspaces with SSO enabled)
   */
  sso?: WorkspaceSsoConfig;
}
```

**Примечание:** Поля в MongoDB появятся автоматически при первом обновлении workspace с SSO конфигурацией.

### 3.2 Обновление типов User

**Файл:** [`types/src/dbScheme/user.ts`](../types/src/dbScheme/user.ts)

**Действия:**
1. Добавить опциональное поле `identities` в интерфейс `UserDBScheme`

**Код:**
```typescript
export interface UserDBScheme {
  // ... существующие поля
  
  /**
   * External identities for SSO (keyed by workspaceId)
   */
  identities?: {
    [workspaceId: string]: {
      saml: {
        /**
         * NameID value from IdP (stable identifier)
         */
        id: string;
        
        /**
         * Email at the time of linking (for audit)
         */
        email: string;
      };
    };
  };
}
```

### 3.3 Обновление `WorkspaceModel`

**Файл:** [`api/src/models/workspace.ts`](../api/src/models/workspace.ts)

**Действия:**
1. Добавить поле `sso` в класс `WorkspaceModel`
2. Добавить методы для работы с SSO (опционально, если нужна бизнес-логика на уровне модели)

**Код:**
```typescript
import { WorkspaceSsoConfig } from '../sso/types';

export default class WorkspaceModel extends AbstractModel<WorkspaceDBScheme> {
  // ... существующие поля
  
  /**
   * SSO configuration
   */
  public sso?: WorkspaceSsoConfig;
  
  // ... существующие методы
}
```

### 3.4 Обновление `UserModel`

**Файл:** [`api/src/models/user.ts`](../api/src/models/user.ts)

**Действия:**
1. Добавить поле `identities` в класс `UserModel`
2. Добавить методы для работы с SSO identities:
   - `linkSamlIdentity(workspaceId: string, samlId: string, email: string): Promise<void>`
   - `findBySamlIdentity(workspaceId: string, samlId: string): Promise<UserModel | null>`
   - `getSamlIdentity(workspaceId: string): { id: string; email: string } | null`

**Код:**
```typescript
export default class UserModel extends AbstractModel<UserDBScheme> {
  // ... существующие поля
  
  /**
   * External identities for SSO
   */
  public identities?: UserDBScheme['identities'];
  
  /**
   * Link SAML identity to user for specific workspace
   */
  public async linkSamlIdentity(
    workspaceId: string,
    samlId: string,
    email: string
  ): Promise<void> {
    const updateData: Partial<UserDBScheme> = {
      [`identities.${workspaceId}.saml.id`]: samlId,
      [`identities.${workspaceId}.saml.email`]: email,
    };
    
    await this.update(
      { _id: new ObjectId(this._id) },
      { $set: updateData }
    );
    
    // Обновить локальное состояние
    if (!this.identities) {
      this.identities = {};
    }
    if (!this.identities[workspaceId]) {
      this.identities[workspaceId] = { saml: { id: samlId, email } };
    } else {
      this.identities[workspaceId].saml = { id: samlId, email };
    }
  }
  
  /**
   * Find user by SAML identity
   */
  public static async findBySamlIdentity(
    collection: Collection<UserDBScheme>,
    workspaceId: string,
    samlId: string
  ): Promise<UserModel | null> {
    const userData = await collection.findOne({
      [`identities.${workspaceId}.saml.id`]: samlId,
    });
    
    return userData ? new UserModel(userData) : null;
  }
  
  /**
   * Get SAML identity for workspace
   */
  public getSamlIdentity(workspaceId: string): { id: string; email: string } | null {
    return this.identities?.[workspaceId]?.saml || null;
  }
}
```

### 3.5 Обновление `UsersFactory`

**Файл:** [`api/src/models/usersFactory.ts`](../api/src/models/usersFactory.ts)

**Действия:**
1. Добавить метод `findBySamlIdentity(workspaceId: string, samlId: string): Promise<UserModel | null>`

**Код:**
```typescript
export default class UsersFactory extends AbstractModelFactory<UserDBScheme, UserModel> {
  // ... существующие методы
  
  /**
   * Find user by SAML identity
   */
  public async findBySamlIdentity(workspaceId: string, samlId: string): Promise<UserModel | null> {
    const userData = await this.collection.findOne({
      [`identities.${workspaceId}.saml.id`]: samlId,
    });
    
    return userData ? new UserModel(userData) : null;
  }
}
```

### 3.6 Тесты для моделей

**Файл:** [`api/test/models/user.test.ts`](../api/test/models/user.test.ts)

**Действия:**
1. Добавить тесты для методов работы с SSO identities:
   - `linkSamlIdentity` — проверка привязки SAML identity к пользователю
   - `findBySamlIdentity` — проверка поиска пользователя по SAML identity
   - Проверка обновления поля `identities` в базе данных

**Примечание:** Тесты пишутся сразу после реализации методов, следуя подходу TDD.

---

## Этап 4: Реализация SAML Service (бизнес-логика)

### 4.1 Создание SAML Service

**Файл:** [`api/src/sso/saml/service.ts`](../api/src/sso/saml/service.ts)

**Действия:**
1. Создать класс `SamlService` с методами:
   - `generateAuthnRequest(workspaceId: string, acsUrl: string, relayState: string): Promise<string>`
   - `validateAndParseResponse(samlResponse: string, workspaceId: string, acsUrl: string): Promise<SamlResponseData>`
   - `validateAudience(audience: string): boolean`
   - `validateRecipient(recipient: string, expectedAcsUrl: string): boolean`
   - `validateInResponseTo(inResponseTo: string, workspaceId: string): Promise<boolean>`
   - `validateTimeConditions(notBefore: Date, notOnOrAfter: Date): boolean`

**Код (структура):**
```typescript
import { SamlConfig, SamlResponseData } from '../types';
import { SamlOptions, SAML } from '@node-saml/node-saml';
import { ObjectId } from 'mongodb';

/**
 * Service for SAML SSO operations
 */
export default class SamlService {
  /**
   * Generate SAML AuthnRequest
   */
  public async generateAuthnRequest(
    workspaceId: string,
    acsUrl: string,
    relayState: string,
    samlConfig: SamlConfig
  ): Promise<string> {
    // Реализация через @node-saml/node-saml
  }
  
  /**
   * Validate and parse SAML Response
   */
  public async validateAndParseResponse(
    samlResponse: string,
    workspaceId: string,
    acsUrl: string,
    samlConfig: SamlConfig
  ): Promise<SamlResponseData> {
    // Реализация валидации и парсинга
  }
  
  // ... остальные методы
}
```

### 4.2 Unit тесты для SAML Service

**Файл:** [`api/test/sso/saml/service.test.ts`](../api/test/sso/saml/service.test.ts)

**Действия:**
1. Написать unit-тесты для методов `SamlService` (TDD подход):
   - Генерация AuthnRequest — проверка корректности формирования запроса
   - Валидация SAML Response — проверка парсинга и валидации
   - Проверка Audience — валидация соответствия `SSO_SP_ENTITY_ID`
   - Проверка Recipient — валидация соответствия ACS URL
   - Проверка InResponseTo — валидация соответствия AuthnRequest ID
   - Проверка временных условий — валидация `NotBefore` и `NotOnOrAfter`

**Примечание:** Тесты пишутся параллельно с реализацией методов, следуя подходу TDD.

### 4.3 Создание хранилища для RelayState и InResponseTo

**Файл:** [`api/src/sso/saml/store.ts`](../api/src/sso/saml/store.ts)

**Действия:**
1. Создать простой in-memory store (или использовать Redis, если доступен)
2. Реализовать методы:
   - `saveRelayState(stateId: string, data: { returnUrl: string; workspaceId: string }): void`
   - `getRelayState(stateId: string): { returnUrl: string; workspaceId: string } | null`
   - `saveAuthnRequest(requestId: string, workspaceId: string): void`
   - `validateAndConsumeAuthnRequest(requestId: string, workspaceId: string): boolean`

**Код (in-memory версия):**
```typescript
/**
 * In-memory store for SAML state
 * TODO: Replace with Redis for production
 */
class SamlStateStore {
  private relayStates: Map<string, { returnUrl: string; workspaceId: string; expiresAt: number }> = new Map();
  private authnRequests: Map<string, { workspaceId: string; expiresAt: number }> = new Map();
  
  private readonly TTL = 5 * 60 * 1000; // 5 minutes
  
  public saveRelayState(stateId: string, data: { returnUrl: string; workspaceId: string }): void {
    this.relayStates.set(stateId, {
      ...data,
      expiresAt: Date.now() + this.TTL,
    });
  }
  
  public getRelayState(stateId: string): { returnUrl: string; workspaceId: string } | null {
    const state = this.relayStates.get(stateId);
    
    if (!state) {
      return null;
    }
    
    if (Date.now() > state.expiresAt) {
      this.relayStates.delete(stateId);
      return null;
    }
    
    return { returnUrl: state.returnUrl, workspaceId: state.workspaceId };
  }
  
  // ... остальные методы
}

export default new SamlStateStore();
```

---

## Этап 5: Реализация SAML HTTP Endpoints

### 5.1 Создание SAML Controller

**Файл:** [`api/src/sso/saml/controller.ts`](../api/src/sso/saml/controller.ts)

**Действия:**
1. Создать класс `SamlController` с методами:
   - `getAcsUrl(workspaceId: string): string` — приватный метод для формирования ACS URL
   - `initiateLogin(req: express.Request, res: express.Response): Promise<void>`
   - `handleAcs(req: express.Request, res: express.Response): Promise<void>`

**Код (структура):**
```typescript
import express from 'express';
import { ObjectId } from 'mongodb';
import SamlService from './service';
import samlStore from './store';
import { ContextFactories } from '../../types/graphql';
import { AuthenticationError, UserInputError } from 'apollo-server-express';
import jwt, { Secret } from 'jsonwebtoken';

/**
 * Controller for SAML SSO endpoints
 */
export default class SamlController {
  private samlService: SamlService;
  private factories: ContextFactories;
  
  constructor(factories: ContextFactories) {
    this.samlService = new SamlService();
    this.factories = factories;
  }
  
  /**
   * Compose Assertion Consumer Service URL for workspace
   * @param workspaceId - workspace ID
   * @returns ACS URL
   */
  private getAcsUrl(workspaceId: string): string {
    const apiUrl = process.env.API_URL || 'http://localhost:4000';
    return `${apiUrl}/auth/sso/saml/${workspaceId}/acs`;
  }
  
  /**
   * Initiate SSO login (GET /auth/sso/saml/:workspaceId)
   */
  public async initiateLogin(req: express.Request, res: express.Response): Promise<void> {
    const { workspaceId } = req.params;
    const returnUrl = req.query.returnUrl as string || `/workspace/${workspaceId}`;
    
    /**
     * 1. Check if workspace has SSO enabled
     */
    const workspace = await this.factories.workspacesFactory.findById(workspaceId);
    
    if (!workspace || !workspace.sso?.enabled) {
      res.status(400).json({ error: 'SSO is not enabled for this workspace' });
      return;
    }
    
    /**
     * 2. Compose Assertion Consumer Service URL
     */
    const acsUrl = this.getAcsUrl(workspaceId);
    const relayStateId = crypto.randomUUID();
    
    /**
     * 3. Save RelayState to temporary storage
     */
    samlStore.saveRelayState(relayStateId, { returnUrl, workspaceId });
    
    /**
     * 4. Generate AuthnRequest
     */
    const authnRequest = await this.samlService.generateAuthnRequest(
      workspaceId,
      acsUrl,
      relayStateId,
      workspace.sso.saml
    );
    
    /**
     * 5. Redirect to IdP
     */
    const redirectUrl = new URL(workspace.sso.saml.ssoUrl);
    redirectUrl.searchParams.set('SAMLRequest', authnRequest);
    redirectUrl.searchParams.set('RelayState', relayStateId);
    
    res.redirect(redirectUrl.toString());
  }
  
  /**
   * Handle ACS callback (POST /auth/sso/saml/:workspaceId/acs)
   */
  public async handleAcs(req: express.Request, res: express.Response): Promise<void> {
    const { workspaceId } = req.params;
    const samlResponse = req.body.SAMLResponse as string;
    const relayStateId = req.body.RelayState as string;
    
    /**
     * 1. Get workspace SSO configuration and check if SSO is enabled
     */
    const workspace = await this.factories.workspacesFactory.findById(workspaceId);
    
    if (!workspace || !workspace.sso?.enabled) {
      res.status(400).json({ error: 'SSO is not enabled' });
      return;
    }
    
    /**
     * 2. Validate and parse SAML Response
     */
    const acsUrl = this.getAcsUrl(workspaceId);
    
    let samlData: SamlResponseData;
    try {
      samlData = await this.samlService.validateAndParseResponse(
        samlResponse,
        workspaceId,
        acsUrl,
        workspace.sso.saml
      );
    } catch (error) {
      console.error('SAML validation error:', error);
      res.status(400).json({ error: 'Invalid SAML response' });
      return;
    }

    /**
     * 3. Find or create user
     */
    let user = await this.factories.usersFactory.findBySamlIdentity(workspaceId, samlData.nameId);
    
    if (!user) {
      /**
       * JIT provisioning or invite-only policy
       * @todo Implement access policy
       */
      user = await this.handleUserProvisioning(workspaceId, samlData, workspace);
    }
    
    /**
     * 4. Create Hawk session
     */
    const tokens = await user.generateTokensPair();
    
    /**
     * 5. Get RelayState and redirect
     */
    const relayState = samlStore.getRelayState(relayStateId);
    const returnUrl = relayState?.returnUrl || `/workspace/${workspaceId}`;
    
    /**
     * 6. Redirect to Garage with tokens
     */
    const frontendUrl = new URL(returnUrl, process.env.GARAGE_URL);
    frontendUrl.searchParams.set('access_token', tokens.accessToken);
    frontendUrl.searchParams.set('refresh_token', tokens.refreshToken);
    
    res.redirect(frontendUrl.toString());
  }
  
  /**
   * Handle user provisioning (JIT or invite-only)
   */
  private async handleUserProvisioning(
    workspaceId: string,
    samlData: SamlResponseData,
    workspace: WorkspaceModel
  ): Promise<UserModel> {
    /**
     * @todo Implement access policy
     * 
     * Right now we create user if it doesn't exist
     * In the future: check invite-only policy
     */
    let user = await this.factories.usersFactory.findByEmail(samlData.email);
    
    if (!user) {
        /**
         * Create new user
         * @todo Implement user creation
         */
        throw new Error('User provisioning not implemented');
    }
    
    /**
     * Link SAML identity
     * @todo Implement SAML identity linking
     */
    await user.linkSamlIdentity(workspaceId, samlData.nameId, samlData.email);
    
    /**
     * Check if user is a member of the workspace
     * @todo Implement workspace membership check. Add user to workspace if it's not a member.
     */
    
    return user;
  }
}
```

### 5.2 Unit тесты для SAML Controller

**Файл:** [`api/test/sso/saml/controller.test.ts`](../api/test/sso/saml/controller.test.ts)

**Действия:**
1. Написать unit-тесты для endpoints (TDD подход):
   - `initiateLogin` — проверка редиректа на IdP, формирования AuthnRequest, сохранения RelayState
   - `handleAcs` — проверка обработки SAML Response, создания сессии, редиректа на фронтенд
   - Проверка ошибок:
     - SSO не включён для workspace
     - Невалидный SAML Response
     - Ошибки валидации (подпись, Audience, Recipient и т.д.)

**Примечание:** Тесты пишутся параллельно с реализацией endpoints, следуя подходу TDD.

### 5.3 Создание SAML Router

**Файл:** [`api/src/sso/saml/index.ts`](../api/src/sso/saml/index.ts)

**Действия:**
1. Создать Express router для SAML endpoints
2. Подключить контроллер

**Код:**
```typescript
import express from 'express';
import SamlController from './controller';
import { ContextFactories } from '../../types/graphql';

/**
 * Create SAML router
 */
export function createSamlRouter(factories: ContextFactories): express.Router {
  const router = express.Router();
  const controller = new SamlController(factories);
  
  /**
   * SSO login initiation
   * GET /auth/sso/saml/:workspaceId
   */
  router.get('/:workspaceId', async (req, res, next) => {
    try {
      await controller.initiateLogin(req, res);
    } catch (error) {
      next(error);
    }
  });
  
  /**
   * ACS callback
   * POST /auth/sso/saml/:workspaceId/acs
   */
  router.post('/:workspaceId/acs', async (req, res, next) => {
    try {
      await controller.handleAcs(req, res);
    } catch (error) {
      next(error);
    }
  });
  
  return router;
}
```

### 5.4 Интеграция SSO модуля в главный сервер

**Файл:** [`api/src/sso/index.ts`](../api/src/sso/index.ts)

**Действия:**
1. Создать главный экспорт SSO модуля
2. Экспортировать функцию для подключения роутов

**Код:**
```typescript
import express from 'express';
import { createSamlRouter } from './saml';
import { ContextFactories } from '../types/graphql';

/**
 * Append SSO routes to Express app
 */
export function appendSsoRoutes(app: express.Application, factories: ContextFactories): void {
  const samlRouter = createSamlRouter(factories);
  app.use('/auth/sso/saml', samlRouter);
}
```

**Файл:** [`api/src/index.ts`](../api/src/index.ts)

**Действия:**
1. Импортировать `appendSsoRoutes`
2. Вызвать после инициализации factories в методе `start()`

**Код:**
```typescript
import { appendSsoRoutes } from './sso';

public async start(): Promise<void> {
  await mongo.setupConnections();
  await rabbitmq.setupConnections();
  
  const dataLoaders = new DataLoaders(mongo.databases.hawk!);
  const factories = HawkAPI.setupFactories(dataLoaders);
  
  appendSsoRoutes(this.app, factories);
  
  await this.server.start();
  // ... remaining code
}
```

---

## Этап 6: GraphQL API для управления SSO настройками

### 6.1 Добавление GraphQL типов

**Файл:** [`api/src/typeDefs/workspace.ts`](../api/src/typeDefs/workspace.ts)

**Действия:**
1. Добавить типы для SSO конфигурации в GraphQL схему
2. Добавить поле `sso` в тип `Workspace` (только для админов)
3. Добавить input типы для обновления SSO
4. Добавить мутацию `updateWorkspaceSso`

**Код:**
```graphql
"""
SAML attribute mapping configuration
"""
input SamlAttributeMappingInput {
  """
  Attribute name for email in SAML Assertion
  Used to map the email attribute from the SAML response to the email attribute in the Hawk database
  """
  email: String!
  
  """
  Attribute name for user name in SAML Assertion
  Used to map the name attribute from the SAML response to the name attribute in the Hawk database
  """
  name: String
}

"""
SAML SSO configuration input
"""
input SamlConfigInput {
  """
  IdP Entity ID
  Used to ensure that the SAML response is coming from the correct IdP
  """
  idpEntityId: String!
  
  """
  SSO URL for redirecting user to IdP
  Used to redirect user to the correct IdP
  """
  ssoUrl: String!
  
  """
  X.509 certificate for signature verification (PEM format)
  Used to verify the signature of the SAML response
  """
  x509Cert: String!
  
  """
  Desired NameID format
  Used to specify the format of the NameID in the SAML response
  """
  nameIdFormat: String
  
  """
  Attribute mapping configuration
  Used to map the attributes from the SAML response to the attributes in the Hawk database
  """
  attributeMapping: SamlAttributeMappingInput!
}

"""
SSO configuration input
"""
input WorkspaceSsoConfigInput {
  """
  Is SSO enabled
  Used to enable or disable SSO for the workspace
  """
  enabled: Boolean!
  
  """
  Is SSO enforced (only SSO login allowed)
  Used to enforce SSO login for the workspace. If true, only SSO login is allowed.
  """
  enforced: Boolean!
  
  """
  SAML-specific configuration
  Used to configure the SAML-specific settings for the workspace
  """
  saml: SamlConfigInput!
}

"""
SSO configuration (admin only)
"""
type WorkspaceSsoConfig {
  """
  Is SSO enabled
  Used to enable or disable SSO for the workspace
  """
  enabled: Boolean!
  
  """
  Is SSO enforced
  Used to enforce SSO login for the workspace. If true, only SSO login is allowed.
  """
  enforced: Boolean!
  
  """
  SSO provider type
  Used to specify the type of the SSO provider for the workspace
  """
  type: String!
  
  """
  SAML-specific configuration
  Used to configure the SAML-specific settings for the workspace
  """
  saml: SamlConfig!
}

"""
SAML configuration
"""
type SamlConfig {
  """
  IdP Entity ID
  Used to ensure that the SAML response is coming from the correct IdP
  """
  idpEntityId: String!
  
  """
  SSO URL
  Used to redirect user to the correct IdP
  """
  ssoUrl: String!
  
  """
  X.509 certificate (masked for security)
  Used to verify the signature of the SAML response
  """
  x509Cert: String!
  
  """
  NameID format
  Used to specify the format of the NameID in the SAML response
  """
  nameIdFormat: String
  
  """
  Attribute mapping
  Used to map the attributes from the SAML response to the attributes in the Hawk database
  """
  attributeMapping: SamlAttributeMapping!
}

"""
SAML attribute mapping
"""
type SamlAttributeMapping {
  """
  Email attribute name
  Used to map the email attribute from the SAML response to the email attribute in the Hawk database
  """
  email: String!
  
  """
  Name attribute name
  Used to map the name attribute from the SAML response to the name attribute in the Hawk database
  """
  name: String
}

extend type Workspace {
  """
  SSO configuration (admin only, not returned in regular queries)
  """
  sso: WorkspaceSsoConfig
}

extend type Query {
  """
  Get SSO settings for workspace (admin only)
  """
  workspaceSsoSettings(workspaceId: ID!): WorkspaceSsoConfig @requireAdmin
}

extend type Mutation {
  """
  Update workspace SSO configuration (admin only)
  """
  updateWorkspaceSso(
    workspaceId: ID!
    config: WorkspaceSsoConfigInput!
  ): Boolean! @requireAdmin
}
```

### 6.2 Реализация резолверов

**Файл:** [`api/src/resolvers/workspace.js`](../api/src/resolvers/workspace.js)

**Действия:**
1. Добавить резолвер для `workspace.sso` (только для админов, не возвращать в обычных запросах)
2. Добавить резолвер для `Query.workspaceSsoSettings`
3. Добавить резолвер для `Mutation.updateWorkspaceSso`

**Код:**
```javascript
/**
 * In Workspace resolvers:
 */
Workspace: {
  /**
   * ... existing resolvers
   */
  
  /**
   * SSO configuration (admin only)
   * Not returned in regular workspaces queries
   * Only available through workspaceSsoSettings query
   */
  async sso(workspace, args, { user, factories }) {
    /**
     * Check if user is admin
     */
    const member = await workspace.getMemberInfo(user.id);
    
    if (!member || !member.isAdmin) {
      return null; 
      /**
       * Throw ForbiddenError if user is not admin
       */
      throw new ForbiddenError('Not enough permissions');
    }
    
    return workspace.sso || null;
  },
},

Query: {
  /**
   * ... existing queries
   */
  
  /**
   * Get SSO settings for workspace (admin only)
   */
  async workspaceSsoSettings(_obj, { workspaceId }, { user, factories }) {
    const workspace = await factories.workspacesFactory.findById(workspaceId);
    
    if (!workspace) {
      throw new UserInputError('Workspace not found');
    }
    
    const member = await workspace.getMemberInfo(user.id);
    
    if (!member || !member.isAdmin) {
      throw new ForbiddenError('Not enough permissions');
    }
    
    return workspace.sso || null;
  },
},

Mutation: {
  /**
   * ... existing mutations
   */
  
  /**
   * Update workspace SSO configuration
   */
  async updateWorkspaceSso(_obj, { workspaceId, config }, { user, factories }) {
    const workspace = await factories.workspacesFactory.findById(workspaceId);
    
    if (!workspace) {
      throw new UserInputError('Workspace not found');
    }
    
    const member = await workspace.getMemberInfo(user.id);
    
    if (!member || !member.isAdmin) {
      throw new ForbiddenError('Not enough permissions');
    }
    
    /**
     * Validate configuration
     */
    if (config.enabled && !config.saml) {
      throw new UserInputError('SAML configuration is required when SSO is enabled');
    }

    await workspace.updateWorkspace({
      ...workspace,
      sso: config.enabled ? {
        enabled: config.enabled,
        enforced: config.enforced || false,
        type: 'saml',
        saml: {
          idpEntityId: config.saml.idpEntityId,
          ssoUrl: config.saml.ssoUrl,
          x509Cert: config.saml.x509Cert,
          nameIdFormat: config.saml.nameIdFormat,
          attributeMapping: {
            email: config.saml.attributeMapping.email,
            name: config.saml.attributeMapping.name,
          },
        },
      } : undefined,
    });
    
    return true;
  },
},
```

**Примечание:** Для безопасности поле `sso` не должно возвращаться в обычных запросах `workspaces`. Можно использовать projection в резолвере или фильтровать на уровне модели.

---

## Этап 7: Фронтенд - SSO Login страница

### 7.1 Создание SSO Login компонента

**Файл:** [`garage/src/components/auth/SsoLogin.vue`](../garage/src/components/auth/SsoLogin.vue)

**Действия:**
1. Создать компонент для SSO логина
2. Реализовать форму для ввода `workspaceId` (или использовать из URL)
3. Добавить кнопку "Continue with SSO"
4. Редирект на API endpoint для инициации SSO

**Код (структура):**
```vue
<template>
  <div class="auth-page">
    <div class="auth-page__form">
      <h1>{{ $t('authPages.ssoLogin.title') }}</h1>
      
      <form @submit.prevent="initiateSso">
        <div v-if="!workspaceIdFromUrl" class="form-field">
          <label>{{ $t('authPages.ssoLogin.workspaceId') }}</label>
          <input
            v-model="workspaceId"
            type="text"
            required
            placeholder="Enter workspace ID"
          />
        </div>
        
        <button type="submit" class="button button--primary">
          {{ $t('authPages.ssoLogin.continue') }}
        </button>
      </form>
      
      <div class="auth-page__alt-link">
        <router-link to="/login">
          {{ $t('authPages.ssoLogin.backToLogin') }}
        </router-link>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SsoLogin',
  data() {
    return {
      workspaceId: this.$route.params.workspaceId || '',
    };
  },
  computed: {
    workspaceIdFromUrl() {
      return !!this.$route.params.workspaceId;
    },
  },
  methods: {
    initiateSso() {
      const apiUrl = process.env.VUE_APP_API_URL || 'http://localhost:4000';
      const returnUrl = this.$route.query.returnUrl || `/workspace/${this.workspaceId}`;
      
      /**
       * Redirect to API endpoint
       */
      window.location.href = `${apiUrl}/auth/sso/saml/${this.workspaceId}?returnUrl=${encodeURIComponent(returnUrl)}`;
    },
  },
};
</script>
```

### 7.2 Добавление роута для SSO Login

**Файл:** [`garage/src/router.ts`](../garage/src/router.ts)

**Действия:**
1. Добавить роут для `/login/sso/:workspaceId?`

**Код:**
```typescript
{
  path: '/login/sso/:workspaceId?',
  name: 'sso-login',
  component: () => import(/* webpackChunkName: 'auth-pages' */ './components/auth/SsoLogin.vue'),
  props: route => ({
    workspaceId: route.params.workspaceId,
  }),
},
```

### 7.3 Обновление обычной страницы Login

**Файл:** [`garage/src/components/auth/Login.vue`](../garage/src/components/auth/Login.vue)

**Действия:**
1. Добавить кнопку "Continue with SSO" на страницу логина
2. При клике открывать форму для ввода `workspaceId` или редирект на `/login/sso`

**Код (добавить в template):**
```vue
<div class="auth-page__sso-section">
  <button
    class="button button--secondary"
    @click="goToSsoLogin"
  >
    {{ $t('authPages.continueWithSso') }}
  </button>
</div>
```

**Код (добавить в methods):**
```javascript
goToSsoLogin() {
  // Можно показать модальное окно для ввода workspaceId
  // Или редирект на /login/sso
  this.$router.push({ name: 'sso-login' });
},
```

---

## Этап 8: Фронтенд - Настройки SSO в Workspace

### 8.1 Создание компонента настроек SSO

**Файл:** [`garage/src/components/workspace/settings/Sso.vue`](../garage/src/components/workspace/settings/Sso.vue)

**Действия:**
1. Создать компонент для настройки SSO
2. Форма с полями:
   - Checkbox "Enable SSO"
   - Checkbox "Enforce SSO" (только если SSO enabled)
   - IdP Entity ID
   - SSO URL
   - X.509 Certificate (textarea)
   - NameID Format (select)
   - Attribute Mapping (email, name)
3. Кнопка "Save"
4. Показывать информацию о SP Entity ID и ACS URL для администратора IdP

**Код (структура):**
```vue
<template>
  <div class="workspace-settings-sso">
    <h2>{{ $t('workspaces.settings.sso.title') }}</h2>
    
    <form @submit.prevent="saveWorkspaceSsoConfig">
      <!-- Enable SSO -->
      <div class="form-field">
        <label>
          <input
            v-model="ssoConfig.enabled"
            type="checkbox"
          />
          {{ $t('workspaces.settings.sso.enable') }}
        </label>
      </div>
      
      <!-- Enforce SSO -->
      <div v-if="ssoConfig.enabled" class="form-field">
        <label>
          <input
            v-model="ssoConfig.enforced"
            type="checkbox"
          />
          {{ $t('workspaces.settings.sso.enforce') }}
        </label>
      </div>
      
      <!-- SAML Configuration -->
      <div v-if="ssoConfig.enabled">
        <!-- IdP Entity ID -->
        <div class="form-field">
          <label>{{ $t('workspaces.settings.sso.idpEntityId') }}</label>
          <input
            v-model="ssoConfig.saml.idpEntityId"
            type="text"
            required
          />
        </div>
        
        <!-- SSO URL -->
        <div class="form-field">
          <label>{{ $t('workspaces.settings.sso.ssoUrl') }}</label>
          <input
            v-model="ssoConfig.saml.ssoUrl"
            type="url"
            required
          />
        </div>
        
        <!-- X.509 Certificate -->
        <div class="form-field">
          <label>{{ $t('workspaces.settings.sso.x509Cert') }}</label>
          <textarea
            v-model="ssoConfig.saml.x509Cert"
            required
            rows="5"
          />
        </div>
        
        <!-- NameID Format -->
        <div class="form-field">
          <label>{{ $t('workspaces.settings.sso.nameIdFormat') }}</label>
          <select v-model="ssoConfig.saml.nameIdFormat">
            <option value="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
              Email Address
            </option>
            <option value="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent">
              Persistent
            </option>
            <option value="urn:oasis:names:tc:SAML:2.0:nameid-format:transient">
              Transient
            </option>
          </select>
        </div>
        
        <!-- Attribute Mapping -->
        <div class="form-field">
          <label>{{ $t('workspaces.settings.sso.attributeMapping.email') }}</label>
          <input
            v-model="ssoConfig.saml.attributeMapping.email"
            type="text"
            required
            placeholder="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
          />
        </div>
        
        <div class="form-field">
          <label>{{ $t('workspaces.settings.sso.attributeMapping.name') }}</label>
          <input
            v-model="ssoConfig.saml.attributeMapping.name"
            type="text"
          />
        </div>
      </div>
      
      <!-- SP Information (read-only) -->
      <div v-if="ssoConfig.enabled" class="sso-info">
        <h3>{{ $t('workspaces.settings.sso.spInfo.title') }}</h3>
        <p>
          <strong>{{ $t('workspaces.settings.sso.spInfo.entityId') }}:</strong>
          {{ spEntityId }}
        </p>
        <p>
          <strong>{{ $t('workspaces.settings.sso.spInfo.acsUrl') }}:</strong>
          {{ acsUrl }}
        </p>
      </div>
      
      <button type="submit" class="button button--primary">
        {{ $t('workspaces.settings.sso.save') }}
      </button>
    </form>
  </div>
</template>

<script>
import { UPDATE_WORKSPACE_SSO, FETCH_WORKSPACE_SSO_SETTINGS } from '@/store/modules/workspace/actionTypes';

export default {
  name: 'WorkspaceSettingsSso',
  props: {
    workspaceId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      ssoConfig: {
        enabled: false,
        enforced: false,
        saml: {
          idpEntityId: '',
          ssoUrl: '',
          x509Cert: '',
          nameIdFormat: 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
          attributeMapping: {
            email: '',
            name: '',
          },
        },
      },
    };
  },
  computed: {
    spEntityId() {
      return process.env.VUE_APP_SSO_SP_ENTITY_ID || 'urn:hawk:tracker:saml';
    },
    acsUrl() {
      const apiUrl = process.env.VUE_APP_API_URL || 'http://localhost:4000';
      return `${apiUrl}/auth/sso/saml/${this.workspaceId}/acs`;
    },
  },
  async created() {
    await this.loadSsoSettings();
  },
  methods: {
    async loadSsoSettings() {
      try {
        const settings = await this.$store.dispatch(FETCH_WORKSPACE_SSO_SETTINGS, this.workspaceId);
        
        if (settings) {
          this.ssoConfig = {
            enabled: settings.enabled,
            enforced: settings.enforced,
            saml: {
              idpEntityId: settings.saml.idpEntityId,
              ssoUrl: settings.saml.ssoUrl,
              x509Cert: settings.saml.x509Cert,
              nameIdFormat: settings.saml.nameIdFormat || 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
              attributeMapping: {
                email: settings.saml.attributeMapping.email,
                name: settings.saml.attributeMapping.name || '',
              },
            },
          };
        }
      } catch (error) {
        console.error('Failed to load SSO settings:', error);
      }
    },
    async saveWorkspaceSsoConfig() {
      try {
        await this.$store.dispatch(UPDATE_WORKSPACE_SSO, {
          workspaceId: this.workspaceId,
          config: this.ssoConfig,
        });
        
        this.$notify.show({
          message: this.$t('workspaces.settings.sso.saved'),
          style: 'success',
        });
      } catch (error) {
        this.$notify.show({
          message: this.$t(`workspaces.settings.sso.errors.${error.message}`),
          style: 'error',
        });
      }
    },
  },
};
</script>
```

### 8.2 Добавление роута для SSO настроек

**Файл:** [`garage/src/router.ts`](../garage/src/router.ts)

**Действия:**
1. Добавить роут в children workspace settings

**Код:**
```typescript
{
  path: 'sso',
  name: 'workspace-settings-sso',
  component: () => import(/* webpackChunkName: 'workspace-settings' */ './components/workspace/settings/Sso.vue'),
  props: true,
},
```

### 8.3 Добавление пункта меню в Layout

**Файл:** [`garage/src/components/workspace/settings/Layout.vue`](../garage/src/components/workspace/settings/Layout.vue)

**Действия:**
1. Добавить ссылку на SSO настройки в меню (только для админов)

**Код:**
```vue
<router-link
  v-if="isAdmin"
  class="settings-window__menu-item workspace-settings__menu-item"
  :to="{ name: 'workspace-settings-sso', params: {workspaceId: workspace.id} }"
>
  {{ $t('workspaces.settings.sso.title') }}
</router-link>
```

### 8.4 Добавление Vuex actions

**Файл:** [`garage/src/store/modules/workspace/actionTypes.js`](../garage/src/store/modules/workspace/actionTypes.js)

**Действия:**
1. Добавить константы для новых actions

**Код:**
```javascript
export const FETCH_WORKSPACE_SSO_SETTINGS = 'FETCH_WORKSPACE_SSO_SETTINGS';
export const UPDATE_WORKSPACE_SSO = 'UPDATE_WORKSPACE_SSO';
```

**Файл:** [`garage/src/store/modules/workspace/index.js`](../garage/src/store/modules/workspace/index.js) (или соответствующий файл)

**Действия:**
1. Добавить actions для работы с SSO настройками

**Код:**
```javascript
import * as workspaceApi from '@/api/workspace';

async [FETCH_WORKSPACE_SSO_SETTINGS]({ commit }, workspaceId) {
  const response = await workspaceApi.getSsoSettings(workspaceId);
  return response.data.workspaceSsoSettings;
},

async [UPDATE_WORKSPACE_SSO]({ commit }, { workspaceId, config }) {
  await workspaceApi.updateSsoSettings(workspaceId, config);
},
```

### 8.5 Добавление API методов

**Файл:** [`garage/src/api/workspace/queries.js`](../garage/src/api/workspace/queries.js) (или соответствующий файл)

**Действия:**
1. Добавить GraphQL queries и mutations для SSO

**Код:**
```javascript
export const GET_SSO_SETTINGS = gql`
  query GetSsoSettings($workspaceId: ID!) {
    workspaceSsoSettings(workspaceId: $workspaceId) {
      enabled
      enforced
      type
      saml {
        idpEntityId
        ssoUrl
        x509Cert
        nameIdFormat
        attributeMapping {
          email
          name
        }
      }
    }
  }
`;

export const UPDATE_SSO_SETTINGS = gql`
  mutation UpdateSsoSettings($workspaceId: ID!, $config: WorkspaceSsoConfigInput!) {
    updateWorkspaceSso(workspaceId: $workspaceId, config: $config)
  }
`;
```

**Файл:** [`garage/src/api/workspace/index.js`](../garage/src/api/workspace/index.js)

**Действия:**
1. Добавить методы для вызова queries/mutations

**Код:**
```javascript
import { GET_SSO_SETTINGS, UPDATE_SSO_SETTINGS } from './queries';
import client from '../client';

export async function getSsoSettings(workspaceId) {
  return client.query({
    query: GET_SSO_SETTINGS,
    variables: { workspaceId },
  });
}

export async function updateSsoSettings(workspaceId, config) {
  return client.mutate({
    mutation: UPDATE_SSO_SETTINGS,
    variables: { workspaceId, config },
  });
}
```

---

## Этап 9: Реализация политики доступа (Provisioning)

### 9.1 Добавление политики в Workspace

**Файл:** `api/src/sso/types.ts`

**Действия:**
1. Добавить тип для политики доступа

**Код:**
```typescript
/**
 * User provisioning policy
 */
export type ProvisioningPolicy = 'invite-only' | 'jit';

/**
 * SSO configuration for workspace
 */
export interface WorkspaceSsoConfig {
  // ... существующие поля
  
  /**
   * User provisioning policy
   */
  provisioningPolicy?: ProvisioningPolicy;
}
```

**Примечание:** В MVP можно использовать одну политику по умолчанию (например, `jit`), но лучше сделать настраиваемой.

### 9.2 Реализация логики provisioning в Controller

**Файл:** `api/src/sso/saml/controller.ts`

**Действия:**
1. Обновить метод `handleUserProvisioning` для поддержки политик:
   - `invite-only`: пользователь должен быть приглашён в workspace
   - `jit`: автоматически добавлять пользователя при первом SSO входе

**Код:**
```typescript
private async handleUserProvisioning(
  workspaceId: string,
  samlData: SamlResponseData,
  workspace: WorkspaceModel
): Promise<UserModel> {
  const policy = workspace.sso?.provisioningPolicy || 'jit';
  
  /**
   * Find user by email
   */
  let user = await this.factories.usersFactory.findByEmail(samlData.email);
  
  if (!user) {
    /**
     * Create new user (only for JIT)
     */
    if (policy === 'jit') {
      user = await this.createUserFromSaml(samlData);
    } else {
      throw new AuthenticationError('User not found and provisioning is invite-only');
    }
  }
  
  /**
   * Check if user is a member of the workspace
   */
  const member = await workspace.getMemberInfo(user._id.toString());
  
  if (!member || WorkspaceModel.isPendingMember(member)) {
    if (policy === 'invite-only') {
      throw new AuthenticationError('User is not a member of this workspace');
    } else if (policy === 'jit') {
      /**
       * Add user to workspace
       */
      await workspace.addMember(user._id.toString());
    }
  }
  
  /**
   * Link SAML identity
   */
  await user.linkSamlIdentity(workspaceId, samlData.nameId, samlData.email);
  
  return user;
}

private async createUserFromSaml(samlData: SamlResponseData): Promise<UserModel> {
  /**
   * Create user without password
   */
  const userData: Partial<UserDBScheme> = {
    email: samlData.email,
    name: samlData.name || samlData.email,
    /**
     * Password is not set - only SSO login is allowed
     */
  };
  
  /**
   * TODO: Use UsersFactory to create user
   */
  /**
   * This requires access to factories, which is already in the controller
   */
  const userId = await this.factories.usersFactory.collection.insertOne(userData);
  
  return new UserModel({
    ...userData,
    _id: userId.insertedId,
  } as UserDBScheme);
}
```

---

## Этап 10: Enforcement (SSO Required)

### 10.1 Проверка enforced в login резолвере

**Файл:** [`api/src/resolvers/user.ts`](../api/src/resolvers/user.ts)

**Действия:**
1. Добавить проверку `workspace.sso.enforced` перед обычным логином
2. Если enforced = true, запретить вход по email/password для этого workspace

**Код:**
```typescript
async login(
  _obj: undefined,
  { email, password }: {email: string; password: string},
  { factories }: ResolverContextBase
): Promise<TokensPair> {
  const user = await factories.usersFactory.findByEmail(email);

  if (!user || !(await user.comparePassword(password))) {
    throw new AuthenticationError('Wrong email or password');
  }

  /**
   * Check if there is a workspace with enforced SSO
   */
  const workspacesIds = await user.getWorkspacesIds([]);
  const workspaces = await factories.workspacesFactory.findManyByIds(workspacesIds);
  
  const enforcedWorkspace = workspaces.find(w => w.sso?.enforced);
  
  if (enforcedWorkspace) {
    throw new AuthenticationError(
      `This workspace requires SSO login. Please use SSO to sign in.`
    );
  }

  return user.generateTokensPair();
}
```

**Примечание:** Это проверяет все workspace пользователя. Можно сделать более точную проверку, если передавать `workspaceId` в login mutation.
**Примечание:** Корнер-кейс: если пользователь входит в несколько workspace, но только в одном из них с enforced SSO - он не сможет войти в другие workspace.

---

## Этап 11: Integration тесты

### 11.1 E2E тесты для SSO

**Файл:** [`api/test/integration/cases/sso.test.ts`](../api/test/integration/cases/sso.test.ts)

**Технологии:**
- **Jest** — тестовый фреймворк
- **ts-jest** — поддержка TypeScript
- **Docker Compose** — для поднятия тестового окружения (API, MongoDB, RabbitMQ, Keycloak)
- **axios** — для HTTP запросов к API (через `apiInstance` из `test/integration/utils`)
- **Keycloak** — SAML IdP для тестирования (в Docker контейнере)

**Действия:**
1. Добавить Keycloak сервис в `docker-compose.test.yml`
2. Настроить Keycloak с SAML конфигурацией для тестового workspace
3. Написать e2e тест:
   - Создать workspace с SSO конфигурацией (через GraphQL или напрямую в MongoDB)
   - Инициировать SSO login через GET `/auth/sso/saml/:workspaceId`
   - Получить SAML Response от Keycloak (через браузерную автоматизацию или мокирование)
   - Отправить SAML Response на POST `/auth/sso/saml/:workspaceId/acs`
   - Проверить валидацию и парсинг Response
   - Проверить создание пользователя (JIT provisioning)
   - Проверить создание сессии Hawk (наличие токенов в редиректе)
   - Проверить редирект на фронтенд с токенами

**Примечание:** Integration тесты пишутся после завершения основной реализации всех компонентов. Для упрощения можно использовать моки SAML Response вместо реального Keycloak на первом этапе.

---

## Этап 12: Логирование и аудит

### 12.1 Добавление логирования SSO операций

**Файл:** [`api/src/sso/saml/controller.ts`](../api/src/sso/saml/controller.ts)

**Действия:**
1. Добавить логирование:
   - Успешные SSO логины
   - Ошибки валидации SAML Response
   - Ошибки provisioning
   - workspaceId (без чувствительных данных)
   - В логах сделать подсветку важной информации через ['sgr']('../api/src/utils/ansi.ts')

**Код:**
```typescript
import { requestLogger } from '../../utils/logger';

// В handleAcs:
try {
  samlData = await this.samlService.validateAndParseResponse(...);
} catch (error) {
  console.error('SAML validation error:', {
    workspaceId,
    error: error.message,
    // Не логируем SAMLResponse целиком
  });
  // ...
}
```

---

## Этап 13: Уменьшение времени жизни сессий для SSO

### 13.1 Обновление времени жизни токенов для SSO пользователей

**Файл:** [`api/src/models/user.ts`](../api/src/models/user.ts)

**Действия:**
1. Обновить метод `generateTokensPair` для проверки SSO workspace
2. Если пользователь входит через SSO в workspace с enforced SSO, использовать короткое время жизни токенов (2 дня вместо 30)

**Код:**
```typescript
public async generateTokensPair(workspaceId?: string): Promise<TokensPair> {
  /**
   * Check if there is an enforced SSO workspace
   */
  let isSsoUser = false;
  
  if (workspaceId) {
    const workspace = await this.factories.workspacesFactory.findById(workspaceId);
    if (workspace?.sso?.enforced) {
      isSsoUser = true;
    }
  }
  
  const refreshTokenExpiry = isSsoUser ? '2d' : '30d';
  
  const accessToken = await jwt.sign(
    { userId: this._id },
    process.env.JWT_SECRET_ACCESS_TOKEN as Secret,
    { expiresIn: '15m' }
  );

  const refreshToken = await jwt.sign(
    { userId: this._id },
    process.env.JWT_SECRET_REFRESH_TOKEN as Secret,
    { expiresIn: refreshTokenExpiry }
  );

  return { accessToken, refreshToken };
}
```

**Проблема:** Нужен доступ к factories в UserModel. Решение: передавать workspaceId и проверять через статический метод или передавать информацию о SSO извне.

**Альтернативное решение:** Передавать информацию о SSO в метод `generateTokensPair` из контроллера.

---

## Этап 14: Документация и финализация

### 14.1 Обновление README

**Действия:**
1. Добавить информацию о SSO в `api/README.md`
2. Описать настройку env переменных
3. Описать процесс настройки SSO для администраторов

### 14.2 Обновление i18n

**Файл:** [`garage/src/i18n/messages/en.json`](../garage/src/i18n/messages/en.json) и [`garage/src/i18n/messages/ru.json`](../garage/src/i18n/messages/ru.json)

**Действия:**
1. Добавить переводы для всех новых строк интерфейса

### 14.3 Проверка безопасности

**Действия:**
1. Убедиться, что SSO конфигурация доступна только админам
2. Проверить, что SAML Response валидируется полностью
3. Проверить, что чувствительные данные не логируются

---

## Порядок выполнения этапов

Рекомендуемый порядок:

1. **Этап 1** — Подготовка (зависимости, env)
2. **Этап 2** — Структура SSO модуля
3. **Этап 3** — Обновление моделей + тесты моделей (TDD)
4. **Этап 4** — SAML Service + unit тесты (TDD подход)
5. **Этап 5** — HTTP Endpoints + unit тесты (TDD подход)
6. **Этап 6** — GraphQL API
7. **Этап 7** — Фронтенд SSO Login
8. **Этап 8** — Фронтенд настройки
9. **Этап 9** — Provisioning политика
10. **Этап 10** — Enforcement
11. **Этап 11** — Integration тесты (e2e)
12. **Этап 12** — Логирование
13. **Этап 13** — Время жизни сессий
14. **Этап 14** — Документация

---

## Заметки и предупреждения

1. **Хранение состояния:** In-memory store для RelayState и AuthnRequest подходит для разработки, но для production нужен Redis или другая персистентная система.

2. **Валидация сертификата:** Убедиться, что библиотека `@node-saml/node-saml` правильно валидирует X.509 сертификаты.

3. **Clock skew:** Учесть разницу во времени между серверами при валидации временных условий.

4. **Безопасность:** Не логировать SAMLResponse целиком, только ошибки валидации.

5. **Тестирование:** Использовать Keycloak в Docker для интеграционных тестов.

6. **Миграции:** Поля в MongoDB появятся автоматически при первом обновлении, миграции не нужны.

---

## Дополнительные улучшения (не в MVP)

- Redis для хранения состояния
- SCIM поддержка
- OIDC поддержка
- Группы и роли из IdP
- SAML Single Logout (SLO)
- Метрики SSO логинов

