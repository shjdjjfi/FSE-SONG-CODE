# PR code evidence available to a researcher

Source-grounded patch excerpts; **not independently blinded, not expertise ground truth**.

## BW10818 — [PR #12187](https://github.com/bitwarden/clients/pull/12187.patch)

Files: 1; target code diff lines: 10; logic cues: 6.

- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `-` `const hwnd = this.windowMain.win.getNativeWindowHandle();`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `+` `const hwnd = Buffer.from("");`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `-` `return (await passwords.isAvailable()) && !isSnapStore();`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `+` `return await passwords.isAvailable();`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `+` `if (isSnapStore()) {`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `+` `return false;`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `+` `}`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `+` ``
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `-` `return await biometrics.prompt(hwnd, this.i18nservice.t("polkitConsentMessage"));`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `+` `return await biometrics.prompt(hwnd, "");`

## BW10818 — [PR #12235](https://github.com/bitwarden/clients/pull/12235.patch)

Files: 4; target code diff lines: 8; logic cues: 0.

- `apps/desktop/src/key-management/biometrics/biometric.renderer-ipc.listener.ts` `+` `// FIXME: Update this file to be type safe and remove this and next line`
- `apps/desktop/src/key-management/biometrics/biometric.renderer-ipc.listener.ts` `+` `// @ts-strict-ignore`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `+` `// FIXME: Update this file to be type safe and remove this and next line`
- `apps/desktop/src/key-management/biometrics/biometric.unix.main.ts` `+` `// @ts-strict-ignore`
- `apps/desktop/src/key-management/biometrics/biometric.windows.main.ts` `+` `// FIXME: Update this file to be type safe and remove this and next line`
- `apps/desktop/src/key-management/biometrics/biometric.windows.main.ts` `+` `// @ts-strict-ignore`
- `apps/desktop/src/key-management/biometrics/biometrics.service.ts` `+` `// FIXME: Update this file to be type safe and remove this and next line`
- `apps/desktop/src/key-management/biometrics/biometrics.service.ts` `+` `// @ts-strict-ignore`

## BW10818 — [PR #12907](https://github.com/bitwarden/clients/pull/12907.patch)

Files: 2; target code diff lines: 4; logic cues: 3.

- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `return BiometricsStatus.HardwareUnavailable;`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `} else {`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` ``
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `return BiometricsStatus.HardwareUnavailable;`

## BW10818 — [PR #13039](https://github.com/bitwarden/clients/pull/13039.patch)

Files: 4; target code diff lines: 61; logic cues: 16.

- `apps/desktop/src/key-management/biometrics/main-biometrics-ipc.listener.ts` `+` `if (message.key == null) {`
- `apps/desktop/src/key-management/biometrics/main-biometrics-ipc.listener.ts` `+` `return;`
- `apps/desktop/src/key-management/biometrics/main-biometrics-ipc.listener.ts` `+` `}`
- `apps/desktop/src/key-management/biometrics/main-biometrics-ipc.listener.ts` `+` `if (message.key == null) {`
- `apps/desktop/src/key-management/biometrics/main-biometrics-ipc.listener.ts` `+` `return;`
- `apps/desktop/src/key-management/biometrics/main-biometrics-ipc.listener.ts` `+` `}`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `this.loadOsBiometricService(this.platform);`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `}`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` ``
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `private loadOsBiometricService(platform: NodeJS.Platform) {`

## BW10818 — [PR #13287](https://github.com/bitwarden/clients/pull/13287.patch)

Files: 3; target code diff lines: 13; logic cues: 3.

- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` ``
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `async canEnableBiometricUnlock(): Promise<boolean> {`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `return true;`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `}`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` ``
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `async canEnableBiometricUnlock(): Promise<boolean> {`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `const biometricStatus = await this.getBiometricsStatus();`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `return [`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `BiometricsStatus.Available,`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `BiometricsStatus.AutoSetupNeeded,`

## BW10818 — [PR #13598](https://github.com/bitwarden/clients/pull/13598.patch)

Files: 2; target code diff lines: 10; logic cues: 2.

- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `import { EncryptionType } from "@bitwarden/common/platform/enums";`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `import { Utils } from "@bitwarden/common/platform/misc/utils";`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `-` `const key = symmetricKey?.macKeyB64 ?? symmetricKey?.keyB64;`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `let key = null;`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `const innerKey = symmetricKey.inner();`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `if (innerKey.type === EncryptionType.AesCbc256_HmacSha256_B64) {`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `key = Utils.fromBufferToB64(innerKey.authenticationKey);`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `} else {`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `key = Utils.fromBufferToB64(innerKey.encryptionKey);`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `}`

## BW10818 — [PR #13609](https://github.com/bitwarden/clients/pull/13609.patch)

Files: 6; target code diff lines: 15; logic cues: 2.

- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `-` `abstract setClientKeyHalfForUser(userId: UserId, value: string): Promise<void>;`
- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `+` `abstract setClientKeyHalfForUser(userId: UserId, value: string | null): Promise<void>;`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `private clientKeyHalves = new Map<string, string>();`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `private clientKeyHalves = new Map<string, string | null>();`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `async setClientKeyHalfForUser(userId: UserId, value: string): Promise<void> {`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `async setClientKeyHalfForUser(userId: UserId, value: string | null): Promise<void> {`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `this.clientKeyHalves.get(userId),`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `this.clientKeyHalves.get(userId) ?? undefined,`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `this.clientKeyHalves.get(userId),`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `this.clientKeyHalves.get(userId) ?? undefined,`

## BW10818 — [PR #14953](https://github.com/bitwarden/clients/pull/14953.patch)

Files: 3; target code diff lines: 289; logic cues: 76.

- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `-` `// Prompts Windows Hello`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `-` `const keyMaterial = await biometrics.deriveKeyMaterial(this._iv);`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `-` `this._osKeyHalf = keyMaterial.keyB64;`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `-` `this._iv = keyMaterial.ivB64;`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `// Ensures that the Windows Hello popup is in the foreground, by bringing the desktop app window to the foreground.`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `const windowFocused = this.windowMain.win.isFocused();`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `const alwaysOnTop = this.windowMain.win.isAlwaysOnTop();`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `if (!windowFocused) {`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `// Show the window in case it was hidden (in tray icon)`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `this.windowMain.win.showInactive();`

## BW10818 — [PR #15047](https://github.com/bitwarden/clients/pull/15047.patch)

Files: 2; target code diff lines: 8; logic cues: 5.

- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `import { SymmetricCryptoKey } from "@bitwarden/common/platform/models/domain/symmetric-crypto-key";`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `-` `return await ipc.keyManagement.biometric.unlockWithBiometricsForUser(userId);`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `const userKey = await ipc.keyManagement.biometric.unlockWithBiometricsForUser(userId);`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `if (userKey == null) {`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `return null;`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `}`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `// Objects received over IPC lose their prototype, so they must be recreated to restore methods and properties.`
- `apps/desktop/src/key-management/biometrics/renderer-biometrics.service.ts` `+` `return SymmetricCryptoKey.fromJSON(userKey) as UserKey;`

## BW10818 — [PR #15070](https://github.com/bitwarden/clients/pull/15070.patch)

Files: 8; target code diff lines: 128; logic cues: 55.

- `apps/desktop/src/key-management/biometrics/main-biometrics-ipc.listener.ts` `-` `this.logService.info(e);`
- `apps/desktop/src/key-management/biometrics/main-biometrics-ipc.listener.ts` `+` `this.logService.error("[Main Biometrics IPC Listener] %s failed", message.action, e);`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `this.osBiometricsService = new OsBiometricsServiceMac(this.i18nService);`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `this.osBiometricsService = new OsBiometricsServiceMac(this.i18nService, this.logService);`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `-` `this.osBiometricsService = new OsBiometricsServiceLinux(this.i18nService, this.windowMain);`
- `apps/desktop/src/key-management/biometrics/main-biometrics.service.ts` `+` `this.osBiometricsService = new OsBiometricsServiceLinux(this.logService);`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `import { I18nService } from "@bitwarden/common/platform/abstractions/i18n.service";`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `+` `import { LogService } from "@bitwarden/common/platform/abstractions/log.service";`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `import { WindowMain } from "../../main/window.main";`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `constructor(`

## BW10818 — [PR #15140](https://github.com/bitwarden/clients/pull/15140.patch)

Files: 10; target code diff lines: 555; logic cues: 167.

- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `+` `import { SymmetricCryptoKey } from "@bitwarden/common/platform/models/domain/symmetric-crypto-key";`
- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `-` `abstract setBiometricProtectedUnlockKeyForUser(userId: UserId, value: string): Promise<void>;`
- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `+` `abstract setBiometricProtectedUnlockKeyForUser(`
- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `+` `userId: UserId,`
- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `+` `value: SymmetricCryptoKey,`
- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `+` `): Promise<void>;`
- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `-` ``
- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `-` ``
- `apps/desktop/src/key-management/biometrics/desktop.biometrics.service.ts` `-` `abstract setClientKeyHalfForUser(userId: UserId, value: string | null): Promise<void>;`
- `apps/desktop/src/key-management/biometrics/main-biometrics-ipc.listener.ts` `+` `import { SymmetricCryptoKey } from "@bitwarden/common/platform/models/domain/symmetric-crypto-key";`

## BW10818 — [PR #15401](https://github.com/bitwarden/clients/pull/15401.patch)

Files: 1; target code diff lines: 0; logic cues: 0.


## BW10818 — [PR #15457](https://github.com/bitwarden/clients/pull/15457.patch)

Files: 2; target code diff lines: 4; logic cues: 0.

- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `+` `import { EncString } from "@bitwarden/common/key-management/crypto/models/enc-string";`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `import { EncString } from "@bitwarden/common/platform/models/domain/enc-string";`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `+` `import { EncString } from "@bitwarden/common/key-management/crypto/models/enc-string";`
- `apps/desktop/src/key-management/biometrics/os-biometrics-windows.service.ts` `-` `import { EncString } from "@bitwarden/common/platform/models/domain/enc-string";`

## BW10818 — [PR #15957](https://github.com/bitwarden/clients/pull/15957.patch)

Files: 1; target code diff lines: 13; logic cues: 9.

- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `const requireClientKeyHalf = await this.biometricStateService.getRequirePasswordOnStart(userId);`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `if (!requireClientKeyHalf) {`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `return null;`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `}`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` ``
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `const requireClientKeyHalf = await this.biometricStateService.getRequirePasswordOnStart(userId);`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `const clientKeyHalfB64 = this.clientKeyHalves.get(userId);`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `const clientKeyHalfSatisfied = !requireClientKeyHalf || !!clientKeyHalfB64;`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `-` `if (!clientKeyHalfSatisfied) {`
- `apps/desktop/src/key-management/biometrics/os-biometrics-linux.service.ts` `+` `if (this.clientKeyHalves.has(userId)) {`

## BW11709 — [PR #11779](https://github.com/bitwarden/clients/pull/11779.patch)

Files: 1; target code diff lines: 7; logic cues: 0.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { AccountInfo } from "@bitwarden/common/auth/abstractions/account.service";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { Account } from "@bitwarden/common/auth/abstractions/account.service";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `async rotateUserKeyAndEncryptedData(`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `masterPassword: string,`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `user: { id: UserId } & AccountInfo,`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `): Promise<void> {`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `async rotateUserKeyAndEncryptedData(masterPassword: string, user: Account): Promise<void> {`

## BW11709 — [PR #12235](https://github.com/bitwarden/clients/pull/12235.patch)

Files: 3; target code diff lines: 4; logic cues: 0.

- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `+` `// @ts-strict-ignore`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `// @ts-strict-ignore`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `+` `// FIXME: Update this file to be type safe and remove this and next line`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `// FIXME: Update this file to be type safe and remove this and next line`

## BW11709 — [PR #12646](https://github.com/bitwarden/clients/pull/12646.patch)

Files: 8; target code diff lines: 339; logic cues: 38.

- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `export class AccountKeysRequest {`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `// Other keys encrypted by the userkey`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `userKeyEncryptedAccountPrivateKey: string;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `accountPublicKey: string;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` ``
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `constructor(userKeyEncryptedAccountPrivateKey: string, accountPublicKey: string) {`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `this.userKeyEncryptedAccountPrivateKey = userKeyEncryptedAccountPrivateKey;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `this.accountPublicKey = accountPublicKey;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `}`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `}`

## BW11709 — [PR #12655](https://github.com/bitwarden/clients/pull/12655.patch)

Files: 8; target code diff lines: 438; logic cues: 58.

- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `export class AccountKeysRequest {`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `// Other keys encrypted by the userkey`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `userKeyEncryptedAccountPrivateKey: string;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `accountPublicKey: string;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` ``
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `constructor(userKeyEncryptedAccountPrivateKey: string, accountPublicKey: string) {`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `this.userKeyEncryptedAccountPrivateKey = userKeyEncryptedAccountPrivateKey;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `this.accountPublicKey = accountPublicKey;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `}`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `}`

## BW11709 — [PR #12935](https://github.com/bitwarden/clients/pull/12935.patch)

Files: 1; target code diff lines: 6; logic cues: 0.

- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `+` `// FIXME: remove src and fix import`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `+` `// eslint-disable-next-line no-restricted-imports`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `+` `// FIXME: remove src and fix import`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `+` `// eslint-disable-next-line no-restricted-imports`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `+` `// FIXME: remove src and fix import`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `+` `// eslint-disable-next-line no-restricted-imports`

## BW11709 — [PR #13121](https://github.com/bitwarden/clients/pull/13121.patch)

Files: 3; target code diff lines: 45; logic cues: 8.

- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `// FIXME: Update this file to be type safe and remove this and next line`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `// @ts-strict-ignore`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `// FIXME: remove src and fix import`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `// eslint-disable-next-line no-restricted-imports`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `import { SendWithIdRequest } from "@bitwarden/common/src/tools/send/models/request/send-with-id.request";`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `// FIXME: remove src and fix import`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `// eslint-disable-next-line no-restricted-imports`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `import { CipherWithIdRequest } from "@bitwarden/common/src/vault/models/request/cipher-with-id.request";`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `// FIXME: remove src and fix import`
- `apps/web/src/app/key-management/key-rotation/request/update-key.request.ts` `-` `// eslint-disable-next-line no-restricted-imports`

## BW11709 — [PR #13194](https://github.com/bitwarden/clients/pull/13194.patch)

Files: 2; target code diff lines: 2; logic cues: 0.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { DeviceTrustServiceAbstraction } from "@bitwarden/common/auth/abstractions/device-trust.service.abstraction";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { DeviceTrustServiceAbstraction } from "@bitwarden/common/key-management/device-trust/abstractions/device-trust.service.abstraction";`

## BW11709 — [PR #13220](https://github.com/bitwarden/clients/pull/13220.patch)

Files: 2; target code diff lines: 2; logic cues: 0.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { EncryptService } from "@bitwarden/common/platform/abstractions/encrypt.service";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { EncryptService } from "@bitwarden/common/key-management/crypto/abstractions/encrypt.service";`

## BW11709 — [PR #13576](https://github.com/bitwarden/clients/pull/13576.patch)

Files: 8; target code diff lines: 359; logic cues: 40.

- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `export class AccountKeysRequest {`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `// Other keys encrypted by the userkey`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `userKeyEncryptedAccountPrivateKey: string;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `accountPublicKey: string;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` ``
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `constructor(userKeyEncryptedAccountPrivateKey: string, accountPublicKey: string) {`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `this.userKeyEncryptedAccountPrivateKey = userKeyEncryptedAccountPrivateKey;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `this.accountPublicKey = accountPublicKey;`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `}`
- `apps/web/src/app/key-management/key-rotation/request/account-keys.request.ts` `+` `}`

## BW11709 — [PR #14080](https://github.com/bitwarden/clients/pull/14080.patch)

Files: 2; target code diff lines: 6; logic cues: 4.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `(await this.encryptService.encrypt(privateKey, newUnencryptedUserKey)).encryptedString!,`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `(`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `await this.encryptService.wrapDecapsulationKey(privateKey, newUnencryptedUserKey)`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `).encryptedString!,`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `return (await this.encryptService.encrypt(privateKey, newUserKey)).encryptedString;`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `return (await this.encryptService.wrapDecapsulationKey(privateKey, newUserKey)).encryptedString;`

## BW11709 — [PR #14539](https://github.com/bitwarden/clients/pull/14539.patch)

Files: 2; target code diff lines: 31; logic cues: 3.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { FeatureFlag } from "@bitwarden/common/enums/feature-flag.enum";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { ConfigService } from "@bitwarden/common/platform/abstractions/config/config.service";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { EncryptedString } from "@bitwarden/common/platform/models/domain/enc-string";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { EncryptedString, EncString } from "@bitwarden/common/platform/models/domain/enc-string";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { SymmetricCryptoKey } from "@bitwarden/common/platform/models/domain/symmetric-crypto-key";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { PureCrypto } from "@bitwarden/sdk-internal";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `private configService: ConfigService,`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `const [newUnencryptedUserKey, newMasterKeyEncryptedUserKey] =`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `await this.keyService.makeUserKey(newMasterKey);`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `let userKeyBytes = PureCrypto.generate_user_key_aes256_cbc_hmac();`

## BW11709 — [PR #14900](https://github.com/bitwarden/clients/pull/14900.patch)

Files: 7; target code diff lines: 3534; logic cues: 591.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { firstValueFrom } from "rxjs";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { firstValueFrom, Observable } from "rxjs";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { HashPurpose } from "@bitwarden/common/platform/enums";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { EncryptionType, HashPurpose } from "@bitwarden/common/platform/enums";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { KeyService } from "@bitwarden/key-management";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { KdfConfig, KdfConfigService, KeyService } from "@bitwarden/key-management";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { CryptoFunctionService } from "@bitwarden/common/key-management/crypto/abstractions/crypto-function.service";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` ``
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `type MasterPasswordAuthenticationAndUnlockData = {`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `masterPassword: string;`

## BW11709 — [PR #14942](https://github.com/bitwarden/clients/pull/14942.patch)

Files: 14; target code diff lines: 4931; logic cues: 726.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { firstValueFrom } from "rxjs";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { firstValueFrom, Observable } from "rxjs";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { HashPurpose } from "@bitwarden/common/platform/enums";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { EncryptionType, HashPurpose } from "@bitwarden/common/platform/enums";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { KeyService } from "@bitwarden/key-management";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { KdfConfig, KdfConfigService, KeyService } from "@bitwarden/key-management";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { CryptoFunctionService } from "@bitwarden/common/key-management/crypto/abstractions/crypto-function.service";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` ``
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `type MasterPasswordAuthenticationAndUnlockData = {`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `masterPassword: string;`

## BW11709 — [PR #14945](https://github.com/bitwarden/clients/pull/14945.patch)

Files: 2; target code diff lines: 153; logic cues: 37.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { MasterPasswordVerification } from "@bitwarden/common/auth/types/verification";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { EncryptedString, EncString } from "@bitwarden/common/platform/models/domain/enc-string";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { EncString } from "@bitwarden/common/platform/models/domain/enc-string";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { UserId } from "@bitwarden/common/types/guid";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { UpdateKeyRequest } from "./request/update-key.request";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` ``
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `/**`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `* Creates a new user key and re-encrypts all required data with the it.`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `* @param masterPassword current master password (used for validation)`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `* @deprecated`

## BW11709 — [PR #15457](https://github.com/bitwarden/clients/pull/15457.patch)

Files: 2; target code diff lines: 2; logic cues: 0.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { EncString } from "@bitwarden/common/key-management/crypto/models/enc-string";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { EncString } from "@bitwarden/common/platform/models/domain/enc-string";`

## BW11709 — [PR #15748](https://github.com/bitwarden/clients/pull/15748.patch)

Files: 1; target code diff lines: 17; logic cues: 10.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { firstValueFrom, Observable } from "rxjs";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { firstValueFrom } from "rxjs";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { firstValueFromOrThrow } from "@bitwarden/common/key-management/utils";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `const masterKeyKdfConfig: KdfConfig = (await this.firstValueFromOrThrow(`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `const masterKeyKdfConfig: KdfConfig = (await firstValueFromOrThrow(`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `const currentUserKey: UserKey = (await this.firstValueFromOrThrow(`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `const currentUserKey: UserKey = (await firstValueFromOrThrow(`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `(await this.firstValueFromOrThrow(`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `(await firstValueFromOrThrow(`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` ``

## BW11709 — [PR #16820](https://github.com/bitwarden/clients/pull/16820.patch)

Files: 1; target code diff lines: 8; logic cues: 2.

- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `import { LogoutService } from "@bitwarden/auth/common";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { VaultTimeoutService } from "@bitwarden/common/key-management/vault-timeout";`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `private vaultTimeoutService: VaultTimeoutService,`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `private logoutService: LogoutService,`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `// temporary until userkey can be better verified`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `await this.vaultTimeoutService.logOut();`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `+` `await this.logoutService.logout(user.id);`
- `apps/web/src/app/key-management/key-rotation/user-key-rotation.service.ts` `-` `import { firstValueFromOrThrow } from "@bitwarden/common/key-management/utils";`

## BW12407 — [PR #12853](https://github.com/bitwarden/clients/pull/12853.patch)

Files: 1; target code diff lines: 8; logic cues: 3.

- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` ``
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `const lastProcessReload = await this.biometricStateService.getLastProcessReload();`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `-` `(await this.biometricStateService.getLastProcessReload()) == null ||`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `-` `Date.now() - (await this.biometricStateService.getLastProcessReload()).getTime() >`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `-` `AUTOPROMPT_BIOMETRICS_PROCESS_RELOAD_DELAY`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `lastProcessReload == null ||`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `isNaN(lastProcessReload.getTime()) ||`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `Date.now() - lastProcessReload.getTime() > AUTOPROMPT_BIOMETRICS_PROCESS_RELOAD_DELAY`

## BW12407 — [PR #12854](https://github.com/bitwarden/clients/pull/12854.patch)

Files: 1; target code diff lines: 15; logic cues: 5.

- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` ``
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `const lastProcessReload = await this.biometricStateService.getLastProcessReload();`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `-` `(await this.biometricStateService.getLastProcessReload()) == null ||`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `-` `Date.now() - (await this.biometricStateService.getLastProcessReload()).getTime() >`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `-` `AUTOPROMPT_BIOMETRICS_PROCESS_RELOAD_DELAY`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `lastProcessReload == null ||`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `isNaN(lastProcessReload.getTime()) ||`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `Date.now() - lastProcessReload.getTime() > AUTOPROMPT_BIOMETRICS_PROCESS_RELOAD_DELAY`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `-` `import { ClientType } from "@bitwarden/common/enums";`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `import { ClientType, DeviceType } from "@bitwarden/common/enums";`

## BW12407 — [PR #12875](https://github.com/bitwarden/clients/pull/12875.patch)

Files: 1; target code diff lines: 4; logic cues: 2.

- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `// this account may be unlocked, prevent any prompts so we can redirect to vault`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `if (await this.keyService.hasUserKeyInMemory(activeAccount.id)) {`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `return;`
- `libs/key-management/src/angular/lock/components/lock.component.ts` `+` `}`

## BW12407 — [PR #12928](https://github.com/bitwarden/clients/pull/12928.patch)

Files: 1; target code diff lines: 0; logic cues: 0.


## BW12407 — [PR #13093](https://github.com/bitwarden/clients/pull/13093.patch)

Files: 0; target code diff lines: 0; logic cues: 0.


## BW12927 — [PR #14797](https://github.com/bitwarden/clients/pull/14797.patch)

Files: 1; target code diff lines: 1; logic cues: 0.

- `apps/desktop/src/billing/app/accounts/premium.component.ts` `+` `standalone: false,`

## BW12927 — [PR #16042](https://github.com/bitwarden/clients/pull/16042.patch)

Files: 1; target code diff lines: 0; logic cues: 0.


## BW12927 — [PR #16373](https://github.com/bitwarden/clients/pull/16373.patch)

Files: 1; target code diff lines: 0; logic cues: 0.


## BW12927 — [PR #16461](https://github.com/bitwarden/clients/pull/16461.patch)

Files: 1; target code diff lines: 0; logic cues: 0.


## BW12927 — [PR #16944](https://github.com/bitwarden/clients/pull/16944.patch)

Files: 1; target code diff lines: 2; logic cues: 0.

- `apps/desktop/src/billing/app/accounts/premium.component.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-764): Migrate to OnPush`
- `apps/desktop/src/billing/app/accounts/premium.component.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-on-push-component-change-detection`

## BW13285 — [PR #14277](https://github.com/bitwarden/clients/pull/14277.patch)

Files: 3; target code diff lines: 73; logic cues: 17.

- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `import { PureCrypto } from "@bitwarden/sdk-internal";`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `import {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `DefaultFeatureFlagValue,`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `FeatureFlag,`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `getFeatureFlagValue,`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `} from "../../../enums/feature-flag.enum";`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `protected useSDKForDecryption: boolean = DefaultFeatureFlagValue[FeatureFlag.UseSDKForDecryption];`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` ``
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `return;`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `const old = this.useSDKForDecryption;`

## BW13285 — [PR #14388](https://github.com/bitwarden/clients/pull/14388.patch)

Files: 2; target code diff lines: 14; logic cues: 7.

- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `if (this.blockType0) {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `if (key.inner().type === EncryptionType.AesCbc256_B64 || key.key.byteLength < 64) {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `throw new Error("Type 0 encryption is not supported.");`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `}`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `}`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` ``
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `if (key == null) {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `throw new Error("No encryption key provided.");`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `}`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` ``

## BW13285 — [PR #14398](https://github.com/bitwarden/clients/pull/14398.patch)

Files: 2; target code diff lines: 96; logic cues: 37.

- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `// Handle updating private properties to turn on/off feature flags.`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `onServerConfigChange(newConfig: ServerConfig): void {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `this.blockType0 = getFeatureFlagValue(newConfig, FeatureFlag.PM17987_BlockType0);`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `// Proxy functions; Their implementation are temporary before moving at this level to the SDK`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `async encryptString(plainValue: string, key: SymmetricCryptoKey): Promise<EncString> {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `return this.encrypt(plainValue, key);`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `async encrypt(plainValue: string | Uint8Array, key: SymmetricCryptoKey): Promise<EncString> {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `if (key == null) {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `throw new Error("No encryption key provided.");`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `}`

## BW13285 — [PR #14432](https://github.com/bitwarden/clients/pull/14432.patch)

Files: 1; target code diff lines: 2; logic cues: 2.

- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `if (key.inner().type === EncryptionType.AesCbc256_B64 || key.key.byteLength < 64) {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `if (key.inner().type === EncryptionType.AesCbc256_B64) {`

## BW13285 — [PR #14434](https://github.com/bitwarden/clients/pull/14434.patch)

Files: 1; target code diff lines: 0; logic cues: 0.


## BW13285 — [PR #14538](https://github.com/bitwarden/clients/pull/14538.patch)

Files: 10; target code diff lines: 870; logic cues: 259.

- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `// Handle updating private properties to turn on/off feature flags.`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `onServerConfigChange(newConfig: ServerConfig): void {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `this.blockType0 = getFeatureFlagValue(newConfig, FeatureFlag.PM17987_BlockType0);`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `// Proxy functions; Their implementation are temporary before moving at this level to the SDK`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `async encryptString(plainValue: string, key: SymmetricCryptoKey): Promise<EncString> {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `return this.encrypt(plainValue, key);`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `async encrypt(plainValue: string | Uint8Array, key: SymmetricCryptoKey): Promise<EncString> {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `if (key == null) {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `throw new Error("No encryption key provided.");`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `}`

## BW13285 — [PR #14942](https://github.com/bitwarden/clients/pull/14942.patch)

Files: 3; target code diff lines: 325; logic cues: 155.

- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `// Handle updating private properties to turn on/off feature flags.`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `onServerConfigChange(newConfig: ServerConfig): void {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `this.blockType0 = getFeatureFlagValue(newConfig, FeatureFlag.PM17987_BlockType0);`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `// Proxy functions; Their implementation are temporary before moving at this level to the SDK`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `async encryptString(plainValue: string, key: SymmetricCryptoKey): Promise<EncString> {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `return this.encrypt(plainValue, key);`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `async encrypt(plainValue: string | Uint8Array, key: SymmetricCryptoKey): Promise<EncString> {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `if (key == null) {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `throw new Error("No encryption key provided.");`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `}`

## BW13285 — [PR #15153](https://github.com/bitwarden/clients/pull/15153.patch)

Files: 11; target code diff lines: 1162; logic cues: 303.

- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `// Handle updating private properties to turn on/off feature flags.`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `onServerConfigChange(newConfig: ServerConfig): void {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `this.blockType0 = getFeatureFlagValue(newConfig, FeatureFlag.PM17987_BlockType0);`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `// Proxy functions; Their implementation are temporary before moving at this level to the SDK`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `async encryptString(plainValue: string, key: SymmetricCryptoKey): Promise<EncString> {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `+` `return this.encrypt(plainValue, key);`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `async encrypt(plainValue: string | Uint8Array, key: SymmetricCryptoKey): Promise<EncString> {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `if (key == null) {`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `throw new Error("No encryption key provided.");`
- `libs/common/src/key-management/crypto/services/encrypt.service.implementation.ts` `-` `}`

## BW14571 — [PR #16987](https://github.com/bitwarden/clients/pull/16987.patch)

Files: 4; target code diff lines: 8; logic cues: 8.

- `apps/web/src/app/dirt/reports/pages/organizations/exposed-passwords-report.component.ts` `-` `return this.cipherService.getAllFromApiForOrganization(this.organization.id);`
- `apps/web/src/app/dirt/reports/pages/organizations/exposed-passwords-report.component.ts` `+` `return this.cipherService.getAllFromApiForOrganization(this.organization.id, true);`
- `apps/web/src/app/dirt/reports/pages/organizations/reused-passwords-report.component.ts` `-` `return this.cipherService.getAllFromApiForOrganization(this.organization.id);`
- `apps/web/src/app/dirt/reports/pages/organizations/reused-passwords-report.component.ts` `+` `return this.cipherService.getAllFromApiForOrganization(this.organization.id, true);`
- `apps/web/src/app/dirt/reports/pages/organizations/unsecured-websites-report.component.ts` `-` `return this.cipherService.getAllFromApiForOrganization(this.organization.id);`
- `apps/web/src/app/dirt/reports/pages/organizations/unsecured-websites-report.component.ts` `+` `return this.cipherService.getAllFromApiForOrganization(this.organization.id, true);`
- `apps/web/src/app/dirt/reports/pages/organizations/weak-passwords-report.component.ts` `-` `return this.cipherService.getAllFromApiForOrganization(this.organization.id);`
- `apps/web/src/app/dirt/reports/pages/organizations/weak-passwords-report.component.ts` `+` `return this.cipherService.getAllFromApiForOrganization(this.organization.id, true);`

## BW14571 — [PR #17189](https://github.com/bitwarden/clients/pull/17189.patch)

Files: 1; target code diff lines: 0; logic cues: 0.


## BW14571 — [PR #17434](https://github.com/bitwarden/clients/pull/17434.patch)

Files: 5; target code diff lines: 132; logic cues: 35.

- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `-` `getAllCiphers(): Promise<CipherView[]> {`
- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `-` `return this.cipherService.getAllFromApiForOrganization(this.organization.id);`
- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `+` `async getAllCiphers(): Promise<CipherView[]> {`
- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `+` `const baseCiphers = await super.getAllCiphers();`
- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `+` `const orgCiphers = await this.cipherService.getAllFromApiForOrganization(`
- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `+` `this.organization.id,`
- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `+` `true,`
- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `+` `);`
- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `+` ``
- `apps/web/src/app/dirt/reports/pages/organizations/inactive-two-factor-report.component.ts` `+` `const cipherMap = new Map<string, CipherView>();`

## BW14987 — [PR #15041](https://github.com/bitwarden/clients/pull/15041.patch)

Files: 1; target code diff lines: 1; logic cues: 0.

- `libs/dirt/card/src/card.component.ts` `-` `standalone: true,`

## BW14987 — [PR #16562](https://github.com/bitwarden/clients/pull/16562.patch)

Files: 2; target code diff lines: 0; logic cues: 0.


## BW14987 — [PR #16939](https://github.com/bitwarden/clients/pull/16939.patch)

Files: 1; target code diff lines: 8; logic cues: 0.

- `libs/dirt/card/src/card.component.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-764): Migrate to OnPush`
- `libs/dirt/card/src/card.component.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-on-push-component-change-detection`
- `libs/dirt/card/src/card.component.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-903): Migrate to Signals`
- `libs/dirt/card/src/card.component.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-signals`
- `libs/dirt/card/src/card.component.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-903): Migrate to Signals`
- `libs/dirt/card/src/card.component.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-signals`
- `libs/dirt/card/src/card.component.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-903): Migrate to Signals`
- `libs/dirt/card/src/card.component.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-signals`

## BW14987 — [PR #16952](https://github.com/bitwarden/clients/pull/16952.patch)

Files: 2; target code diff lines: 8; logic cues: 0.

- `libs/dirt/card/src/card.component.ts` `-` `import { TypographyModule } from "@bitwarden/components";`
- `libs/dirt/card/src/card.component.ts` `+` `import { TypographyModule, CardComponent as BitCardComponent } from "@bitwarden/components";`
- `libs/dirt/card/src/card.component.ts` `-` `imports: [CommonModule, TypographyModule, JslibModule],`
- `libs/dirt/card/src/card.component.ts` `-` `host: {`
- `libs/dirt/card/src/card.component.ts` `-` `class:`
- `libs/dirt/card/src/card.component.ts` `-` `"tw-box-border tw-bg-background tw-block tw-text-main tw-border-solid tw-border tw-border-secondary-300 tw-border [&:not(bit-layout_*)]:tw-rounded-lg tw-rounded-lg tw-p-6",`
- `libs/dirt/card/src/card.component.ts` `-` `},`
- `libs/dirt/card/src/card.component.ts` `+` `imports: [CommonModule, TypographyModule, JslibModule, BitCardComponent],`

## BW15093 — [PR #15273](https://github.com/bitwarden/clients/pull/15273.patch)

Files: 6; target code diff lines: 45; logic cues: 2.

- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `@Input() hideCardWrapper: boolean = false;`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `hideCardWrapper: false,`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `export const HideCardWrapper: Story = {`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `render: (args) => ({`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `props: {`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `...args,`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `hideCardWrapper: true,`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `},`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `template: `
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `<auth-anon-layout [title]="title" [subtitle]="subtitle" [showReadonlyHostname]="showReadonlyHostname" [hideLogo]="hideLogo" [hideCardWrapper]="hideCardWrapper">`

## BW15093 — [PR #15340](https://github.com/bitwarden/clients/pull/15340.patch)

Files: 3; target code diff lines: 93; logic cues: 4.

- `libs/components/src/anon-layout/anon-layout.component.ts` `-` `import { Component, HostBinding, Input, OnChanges, OnInit, SimpleChanges } from "@angular/core";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `import {`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `Component,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `HostBinding,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `Input,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `OnChanges,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `OnInit,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `SimpleChanges,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `input,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `} from "@angular/core";`

## BW15093 — [PR #15362](https://github.com/bitwarden/clients/pull/15362.patch)

Files: 6; target code diff lines: 552; logic cues: 30.

- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `import { AnonLayoutComponent } from "./anon-layout.component";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `import { AnonLayoutComponent, AnonLayoutMaxWidths } from "./anon-layout.component";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `maxWidth?: "md" | "3xl";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `/**`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `* Optional flag to set the max-width of the title area. Defaults to null if not provided.`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `*/`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `titleAreaMaxWidth?: "md";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `maxWidth?: AnonLayoutMaxWidths;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `protected maxWidth: "md" | "3xl";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `protected titleAreaMaxWidth: "md";`

## BW15093 — [PR #15375](https://github.com/bitwarden/clients/pull/15375.patch)

Files: 2; target code diff lines: 9; logic cues: 1.

- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `/**`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `* Hides the default Bitwarden shield icon.`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `*/`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `hideIcon?: boolean;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `protected hideIcon: boolean = false;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `if (firstChildRouteData["hideIcon"] !== undefined) {`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `this.hideIcon = firstChildRouteData["hideIcon"];`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `}`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` ``

## BW15093 — [PR #15522](https://github.com/bitwarden/clients/pull/15522.patch)

Files: 1; target code diff lines: 4; logic cues: 0.

- `libs/components/src/anon-layout/anon-layout.component.ts` `-` `import { BitwardenShield } from "../icon/logos";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `import { AnonLayoutBitwardenShield } from "../icon/logos";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `-` `this.icon = BitwardenShield;`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `this.icon = AnonLayoutBitwardenShield;`

## BW15093 — [PR #15610](https://github.com/bitwarden/clients/pull/15610.patch)

Files: 1; target code diff lines: 1; logic cues: 0.

- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `this.hideIcon = null;`

## BW15093 — [PR #15620](https://github.com/bitwarden/clients/pull/15620.patch)

Files: 1; target code diff lines: 4; logic cues: 2.

- `libs/components/src/anon-layout/anon-layout.component.ts` `-` `export type AnonLayoutMaxWidth = "md" | "lg" | "xl" | "2xl" | "3xl";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `export type AnonLayoutMaxWidth = "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `case "4xl":`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `return "tw-max-w-4xl";`

## BW15093 — [PR #15738](https://github.com/bitwarden/clients/pull/15738.patch)

Files: 2; target code diff lines: 28; logic cues: 2.

- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `// FIXME: Update this file to be type safe and remove this and next line`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `// @ts-strict-ignore`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `import { Subject, filter, switchMap, takeUntil, tap } from "rxjs";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `import { Subject, filter, of, switchMap, takeUntil, tap } from "rxjs";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `protected pageTitle: string;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `protected pageSubtitle: string;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `protected pageIcon: Icon;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `protected showReadonlyHostname: boolean;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `protected maxWidth: AnonLayoutMaxWidth;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `protected hideCardWrapper: boolean;`

## BW15093 — [PR #15777](https://github.com/bitwarden/clients/pull/15777.patch)

Files: 1; target code diff lines: 20; logic cues: 0.

- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `import { ChangeDetectorRef, Component, OnDestroy, OnInit } from "@angular/core";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `import { ChangeDetectorRef, Component, OnInit, inject, DestroyRef } from "@angular/core";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `import { takeUntilDestroyed } from "@angular/core/rxjs-interop";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `import { Subject, filter, switchMap, takeUntil, tap } from "rxjs";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `import { filter, switchMap, tap } from "rxjs";`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `export class AnonLayoutWrapperComponent implements OnInit, OnDestroy {`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `private destroy$ = new Subject<void>();`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` ``
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `export class AnonLayoutWrapperComponent implements OnInit {`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `private readonly destroyRef = inject(DestroyRef);`

## BW15093 — [PR #15827](https://github.com/bitwarden/clients/pull/15827.patch)

Files: 1; target code diff lines: 8; logic cues: 2.

- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `if (data.hideIcon !== undefined) {`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `this.hideIcon = data.hideIcon;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `}`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` ``
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `if (data.maxWidth !== undefined) {`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `this.maxWidth = data.maxWidth;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `}`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` ``

## BW15093 — [PR #15892](https://github.com/bitwarden/clients/pull/15892.patch)

Files: 1; target code diff lines: 2; logic cues: 0.

- `libs/components/src/anon-layout/anon-layout.stories.ts` `-` `<button bitButton>Perform Action</button>`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `<button type="button" bitButton>Perform Action</button>`

## BW15093 — [PR #16002](https://github.com/bitwarden/clients/pull/16002.patch)

Files: 5; target code diff lines: 25; logic cues: 0.

- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `import { LeftIllustration, RightIllustration } from "./illustrations";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` ``
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `readonly leftIllustration = LeftIllustration;`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `readonly rightIllustration = RightIllustration;`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` ``
- `libs/components/src/anon-layout/illustrations/index.ts` `+` `export * from "./left-illustration";`
- `libs/components/src/anon-layout/illustrations/index.ts` `+` `export * from "./right-illustration";`
- `libs/components/src/anon-layout/illustrations/left-illustration.ts` `+` `import { svgIcon } from "@bitwarden/components";`
- `libs/components/src/anon-layout/illustrations/left-illustration.ts` `+` ``
- `libs/components/src/anon-layout/illustrations/left-illustration.ts` `+` `export const LeftIllustration = svgIcon`

## BW15093 — [PR #16020](https://github.com/bitwarden/clients/pull/16020.patch)

Files: 6; target code diff lines: 38; logic cues: 0.

- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `import { AnonLayoutBitwardenShield, Icon } from "@bitwarden/icons";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `-` `import { IconModule, Icon } from "../icon";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `import { IconModule } from "../icon";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `-` `import { AnonLayoutBitwardenShield } from "../icon/logos";`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `+` `import { LockIcon, RegistrationCheckEmailIcon } from "@bitwarden/icons";`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `-` `import { LockIcon, RegistrationCheckEmailIcon } from "../icon/icons";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `-` `import { AnonLayoutBitwardenShield, Icon } from "@bitwarden/icons";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `import { AnonLayoutBitwardenShield, BitwardenLogo, Icon } from "@bitwarden/icons";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `-` `import { BitwardenLogo } from "../icon/icons";`
- `libs/components/src/anon-layout/anon-layout.stories.ts` `+` `import { Icon, LockIcon } from "@bitwarden/icons";`

## BW15093 — [PR #16219](https://github.com/bitwarden/clients/pull/16219.patch)

Files: 1; target code diff lines: 0; logic cues: 0.


## BW15093 — [PR #16349](https://github.com/bitwarden/clients/pull/16349.patch)

Files: 1; target code diff lines: 0; logic cues: 0.


## BW15093 — [PR #16433](https://github.com/bitwarden/clients/pull/16433.patch)

Files: 8; target code diff lines: 69; logic cues: 5.

- `libs/components/src/anon-layout/anon-layout-wrapper-data.service.ts` `-` `abstract setAnonLayoutWrapperData(data: AnonLayoutWrapperData): void;`
- `libs/components/src/anon-layout/anon-layout-wrapper-data.service.ts` `+` `abstract setAnonLayoutWrapperData(data: Partial<AnonLayoutWrapperData>): void;`
- `libs/components/src/anon-layout/anon-layout-wrapper-data.service.ts` `-` `abstract anonLayoutWrapperData$(): Observable<AnonLayoutWrapperData>;`
- `libs/components/src/anon-layout/anon-layout-wrapper-data.service.ts` `+` `abstract anonLayoutWrapperData$(): Observable<Partial<AnonLayoutWrapperData>>;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `* The optional icon to display on the page.`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `* The icon to display on the page. Pass null to hide the icon.`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `pageIcon?: Icon | null;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `/**`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `* Hides the default Bitwarden shield icon.`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `-` `*/`

## BW15093 — [PR #16748](https://github.com/bitwarden/clients/pull/16748.patch)

Files: 5; target code diff lines: 20; logic cues: 1.

- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `/**`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `* Hides the background illustration. Defaults to false.`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `*/`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `hideBackgroundIllustration?: boolean;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `protected hideBackgroundIllustration?: boolean | null;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `this.hideBackgroundIllustration = Boolean(firstChildRouteData["hideBackgroundIllustration"]);`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `if (data.hideBackgroundIllustration !== undefined) {`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `this.hideBackgroundIllustration = data.hideBackgroundIllustration;`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `}`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` ``

## BW15093 — [PR #16940](https://github.com/bitwarden/clients/pull/16940.patch)

Files: 3; target code diff lines: 12; logic cues: 0.

- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-764): Migrate to OnPush`
- `libs/components/src/anon-layout/anon-layout-wrapper.component.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-on-push-component-change-detection`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-764): Migrate to OnPush`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-on-push-component-change-detection`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-764): Migrate to OnPush`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-on-push-component-change-detection`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-764): Migrate to OnPush`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-on-push-component-change-detection`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `+` `// FIXME(https://bitwarden.atlassian.net/browse/CL-764): Migrate to OnPush`
- `libs/components/src/anon-layout/anon-layout-wrapper.stories.ts` `+` `// eslint-disable-next-line @angular-eslint/prefer-on-push-component-change-detection`

## BW15093 — [PR #16952](https://github.com/bitwarden/clients/pull/16952.patch)

Files: 2; target code diff lines: 12; logic cues: 0.

- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `import { BaseCardComponent } from "../card/base-card.component";`
- `libs/components/src/anon-layout/anon-layout.component.ts` `-` `imports: [IconModule, CommonModule, TypographyModule, SharedModule, RouterModule],`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `imports: [`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `IconModule,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `CommonModule,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `TypographyModule,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `SharedModule,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `RouterModule,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `BaseCardComponent,`
- `libs/components/src/anon-layout/anon-layout.component.ts` `+` `],`

## GF104424 — [PR #105068](https://github.com/grafana/grafana/pull/105068.patch)

Files: 13; target code diff lines: 91; logic cues: 14.

- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `model "github.com/grafana/grafana/apps/alerting/notifications/pkg/apis/receiver/v0alpha1"`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `model "github.com/grafana/grafana/apps/alerting/notifications/pkg/apis/alerting/v0alpha1"`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `if selector != nil && !selector.Empty() && !selector.Matches(model.SelectableFields(k8sResource)) {`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `if selector != nil && !selector.Empty() && !selector.Matches(model.ReceiverSelectableFields(k8sResource)) {`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `spec := model.Spec{`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `spec := model.ReceiverSpec{`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `Integrations: make([]model.Integration, 0, len(receiver.Integrations)),`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `Integrations: make([]model.ReceiverIntegration, 0, len(receiver.Integrations)),`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `spec.Integrations = append(spec.Integrations, model.Integration{`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `spec.Integrations = append(spec.Integrations, model.ReceiverIntegration{`

## GF104424 — [PR #107056](https://github.com/grafana/grafana/pull/107056.patch)

Files: 1; target code diff lines: 10; logic cues: 0.

- `pkg/registry/apps/alerting/notifications/register.go` `+` `"github.com/grafana/grafana/pkg/services/apiserver/builder"`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `Authorizer:          getAuthorizer(ng.Api.AccessControl),`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `LegacyStorageGetter: getLegacyStorage(request.GetNamespaceMapper(cfg), ng),`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `OpenAPIDefGetter:    v0alpha1.GetOpenAPIDefinitions,`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `ManagedKinds:        notificationsResource.GetKinds(),`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `Authorizer:               getAuthorizer(ng.Api.AccessControl),`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `LegacyStorageGetter:      getLegacyStorage(request.GetNamespaceMapper(cfg), ng),`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `OpenAPIDefGetter:         v0alpha1.GetOpenAPIDefinitions,`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `ManagedKinds:             notificationsResource.GetKinds(),`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `AllowedV0Alpha1Resources: []string{builder.AllResourcesAllowed},`

## GF104424 — [PR #109309](https://github.com/grafana/grafana/pull/109309.patch)

Files: 13; target code diff lines: 128; logic cues: 23.

- `pkg/registry/apps/alerting/notifications/register.go` `+` `appsdkapiserver "github.com/grafana/grafana-app-sdk/k8s/apiserver"`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `restclient "k8s.io/client-go/rest"`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `"github.com/grafana/grafana/apps/alerting/notifications/pkg/apis/alerting/v0alpha1"`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `"github.com/grafana/grafana/pkg/services/accesscontrol"`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `"github.com/grafana/grafana/pkg/services/apiserver/builder"`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `"github.com/grafana/grafana/pkg/services/apiserver/builder/runner"`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `"github.com/grafana/grafana/pkg/services/apiserver/appinstaller"`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `type AlertingNotificationsAppProvider struct {`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `app.Provider`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `var (`

## GF104424 — [PR #109969](https://github.com/grafana/grafana/pull/109969.patch)

Files: 1; target code diff lines: 8; logic cues: 1.

- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `Version:               integration.Config.Version,`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` ``
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `config, err := ngmodels.IntegrationConfigFromType(integration.Type)`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `version := &integration.Version`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `if *version == "" {`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `version = nil`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `}`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `config, err := ngmodels.IntegrationConfigFromType(integration.Type, version)`

## GF104424 — [PR #110619](https://github.com/grafana/grafana/pull/110619.patch)

Files: 1; target code diff lines: 13; logic cues: 4.

- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `"github.com/grafana/grafana/pkg/services/ngalert/api/tooling/definitions"`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `DeleteReceiver(ctx context.Context, name string, provenance definitions.Provenance, version string, orgID int64, user identity.Requester) error`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `+` `DeleteReceiver(ctx context.Context, name string, provenance ngmodels.Provenance, version string, orgID int64, user identity.Requester) error`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `//Names:   ctx.QueryStrings("names"), // TODO: Query params.`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `//Limit:   ctx.QueryInt("limit"),`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `//Offset:  ctx.QueryInt("offset"),`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `+` `// Names:   ctx.QueryStrings("names"), // TODO: Query params.`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `+` `// Limit:   ctx.QueryInt("limit"),`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `+` `// Offset:  ctx.QueryInt("offset"),`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `err = s.service.DeleteReceiver(ctx, uid, definitions.Provenance(ngmodels.ProvenanceNone), version, info.OrgID, user) // TODO add support for dry-run option`

## GF104424 — [PR #110839](https://github.com/grafana/grafana/pull/110839.patch)

Files: 1; target code diff lines: 2; logic cues: 0.

- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `Origin:       ngmodels.ResourceOriginGrafana, // Set to Grafana by default.`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `r.SetCanUse(metadata.CanUse)`

## GF104424 — [PR #111338](https://github.com/grafana/grafana/pull/111338.patch)

Files: 4; target code diff lines: 683; logic cues: 132.

- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `AuthorizeTestByUID(context.Context, identity.Requester, string) error`
- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `AuthorizeTestNew(context.Context, identity.Requester) error`
- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `switch attr.GetSubresource() {`
- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `case "test":`
- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `var err error`
- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `if uid == newReceiverNamePlaceholder {`
- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `err = ac.AuthorizeTestNew(ctx, user)`
- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `} else {`
- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `err = ac.AuthorizeTestByUID(ctx, user, uid)`
- `pkg/registry/apps/alerting/notifications/receiver/authorize.go` `+` `}`

## GF104424 — [PR #112010](https://github.com/grafana/grafana/pull/112010.patch)

Files: 1; target code diff lines: 23; logic cues: 5.

- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `alertingNotify "github.com/grafana/alerting/notify"`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `"github.com/grafana/alerting/receivers/schema"`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `Type:                  integration.Config.Type,`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `Type:                  string(integration.Config.Type()),`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `Version:               string(integration.Config.Version),`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `Version:               integration.Config.Version,`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `version := &integration.Version`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `if *version == "" {`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `version = nil`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `}`

## GF104424 — [PR #112880](https://github.com/grafana/grafana/pull/112880.patch)

Files: 1; target code diff lines: 1; logic cues: 0.

- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `+` `Routes: make([]model.RoutingTreeRoute, 0, len(r.Routes)),`

## GF104424 — [PR #114196](https://github.com/grafana/grafana/pull/114196.patch)

Files: 3; target code diff lines: 15; logic cues: 3.

- `pkg/registry/apps/alerting/notifications/templategroup/conversions.go` `+` `"github.com/grafana/alerting/definition"`
- `pkg/registry/apps/alerting/notifications/templategroup/conversions.go` `+` `Kind:            definition.GrafanaTemplateKind,`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `"github.com/grafana/grafana/pkg/services/featuremgmt"`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `return templategroup.NewStorage(api.Templates, namespacer)`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `srv := api.Templates`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `if a.ng.FeatureToggles.IsEnabledGlobally(featuremgmt.FlagAlertingImportAlertmanagerAPI) {`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `srv = srv.WithIncludeImported()`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `}`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `return templategroup.NewStorage(srv, namespacer)`
- `pkg/registry/apps/alerting/notifications/templategroup/conversions.go` `+` `Kind:    model.TemplateGroupTemplateKind(template.Kind),`

## GF104424 — [PR #115442](https://github.com/grafana/grafana/pull/115442.patch)

Files: 1; target code diff lines: 9; logic cues: 0.

- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `ngmodels.ReceiverPermissionReadSecret: "canReadSecrets",`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `ngmodels.ReceiverPermissionAdmin:      "canAdmin",`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `ngmodels.ReceiverPermissionWrite:      "canWrite",`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `ngmodels.ReceiverPermissionDelete:     "canDelete",`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `ngmodels.ReceiverPermissionReadSecret:      "canReadSecrets",`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `ngmodels.ReceiverPermissionAdmin:           "canAdmin",`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `ngmodels.ReceiverPermissionWrite:           "canWrite",`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `ngmodels.ReceiverPermissionDelete:          "canDelete",`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `ngmodels.ReceiverPermissionModifyProtected: "canModifyProtected",`

## GF104424 — [PR #115959](https://github.com/grafana/grafana/pull/115959.patch)

Files: 1; target code diff lines: 15; logic cues: 2.

- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `"github.com/grafana/grafana/pkg/services/ngalert/notifier/legacy_storage"`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `GetReceiver(ctx context.Context, q ngmodels.GetReceiverQuery, user identity.Requester) (*ngmodels.Receiver, error)`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `+` `GetReceiver(ctx context.Context, uid string, decrypt bool, user identity.Requester) (*ngmodels.Receiver, error)`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `name, err := legacy_storage.UidToName(uid)`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `if err != nil {`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `return nil, apierrors.NewNotFound(ResourceInfo.GroupResource(), uid)`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `}`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `q := ngmodels.GetReceiverQuery{`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `OrgID:   info.OrgID,`
- `pkg/registry/apps/alerting/notifications/receiver/legacy_storage.go` `-` `Name:    name,`

## GF104424 — [PR #116308](https://github.com/grafana/grafana/pull/116308.patch)

Files: 2; target code diff lines: 10; logic cues: 3.

- `pkg/registry/apps/alerting/notifications/register.go` `-` `return timeinterval.NewStorage(api.MuteTimings, namespacer)`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `srv := api.MuteTimings`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `//nolint:staticcheck // not yet migrated to OpenFeature`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `if a.ng.FeatureToggles.IsEnabledGlobally(featuremgmt.FlagAlertingImportAlertmanagerAPI) {`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `srv = srv.WithIncludeImported()`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `}`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `return timeinterval.NewStorage(srv, namespacer)`
- `pkg/registry/apps/alerting/notifications/timeinterval/conversions.go` `+` ``
- `pkg/registry/apps/alerting/notifications/timeinterval/conversions.go` `+` `i.SetCanUse(ngmodels.Provenance(interval.Provenance) != ngmodels.ProvenanceConvertedPrometheus)`
- `pkg/registry/apps/alerting/notifications/timeinterval/conversions.go` `+` ``

## GF104424 — [PR #116434](https://github.com/grafana/grafana/pull/116434.patch)

Files: 1; target code diff lines: 83; logic cues: 29.

- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `t, err := alertingNotify.IntegrationTypeFromString(integration.Type)`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `grafanaIntegration, secureFields, err := convertReceiverIntegrationToIntegration(receiver.Spec.Title, integration)`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `var config schema.IntegrationSchemaVersion`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `typeSchema, _ := alertingNotify.GetSchemaForIntegration(t)`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `if integration.Version != "" {`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `var ok bool`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `config, ok = typeSchema.GetVersion(schema.Version(integration.Version))`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `if !ok {`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `return nil, nil, fmt.Errorf("invalid version %s for integration type %s", integration.Version, integration.Type)`
- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `-` `}`

## GF104424 — [PR #116475](https://github.com/grafana/grafana/pull/116475.patch)

Files: 1; target code diff lines: 23; logic cues: 0.

- `pkg/registry/apps/alerting/notifications/register.go` `-` `"github.com/grafana/grafana-app-sdk/app"`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `appsdkapiserver "github.com/grafana/grafana-app-sdk/k8s/apiserver"`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `"github.com/grafana/grafana-app-sdk/simple"`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `"github.com/grafana/grafana-app-sdk/app"`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `appsdkapiserver "github.com/grafana/grafana-app-sdk/k8s/apiserver"`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `"github.com/grafana/grafana-app-sdk/simple"`
- `pkg/registry/apps/alerting/notifications/register.go` `+` ``
- `pkg/registry/apps/alerting/notifications/register.go` `-` `_ appsdkapiserver.AppInstaller       = (*AlertingNotificationsAppInstaller)(nil)`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `_ appinstaller.LegacyStorageProvider = (*AlertingNotificationsAppInstaller)(nil)`
- `pkg/registry/apps/alerting/notifications/register.go` `-` `_ appinstaller.AuthorizerProvider    = (*AlertingNotificationsAppInstaller)(nil)`

## GF104424 — [PR #116563](https://github.com/grafana/grafana/pull/116563.patch)

Files: 1; target code diff lines: 1; logic cues: 0.

- `pkg/registry/apps/alerting/notifications/receiver/conversions.go` `+` `ngmodels.ReceiverPermissionTest:            "canTest",`

## GF104424 — [PR #117061](https://github.com/grafana/grafana/pull/117061.patch)

Files: 4; target code diff lines: 145; logic cues: 40.

- `pkg/registry/apps/alerting/notifications/register.go` `-` `return routingtree.NewStorage(api.Policies, namespacer)`
- `pkg/registry/apps/alerting/notifications/register.go` `+` `return routingtree.NewStorage(api.RouteService, namespacer)`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `+` `"github.com/grafana/grafana/pkg/services/ngalert/notifier/legacy_storage"`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `-` `func ConvertToK8sResource(orgID int64, r definitions.Route, version string, namespacer request.NamespaceMapper) (*model.RoutingTree, error) {`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `+` `func ConvertToK8sResources(orgID int64, routes legacy_storage.ManagedRoutes, namespacer request.NamespaceMapper) (*model.RoutingTreeList, error) {`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `+` `result := &model.RoutingTreeList{`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `+` `Items: make([]model.RoutingTree, 0, len(routes)),`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `+` `}`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `+` `for _, r := range routes {`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `+` `k8sResource, err := ConvertToK8sResource(orgID, r, namespacer)`

## GF104424 — [PR #117090](https://github.com/grafana/grafana/pull/117090.patch)

Files: 1; target code diff lines: 3; logic cues: 0.

- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `-` `"github.com/prometheus/alertmanager/config"`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `-` `Matchers:            make(config.Matchers, 0, len(r.Matchers)),`
- `pkg/registry/apps/alerting/notifications/routingtree/conversions.go` `+` `ObjectMatchers:      make(definitions.ObjectMatchers, 0, len(r.Matchers)),`
