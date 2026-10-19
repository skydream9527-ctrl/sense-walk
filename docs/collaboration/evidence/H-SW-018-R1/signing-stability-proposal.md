# SW-018 · 测试签名稳定性与版本追溯方案（提案，未实施）

## 问题（STAGE-CLOSEOUT 已确认）

1. **签名不稳定**：CI 在 GitHub runner 上构建 debug 包使用 runner 随机生成的
   `debug.keystore`——每次 run 的证书指纹不同（build153 与 build176 实测不同）。
   后果：用户覆盖安装新包时 Android 拒绝（签名冲突），只能卸载重装，
   **卸载会清掉本地会话快照与设置**——与"被动中断 30min 可恢复"的产品体验冲突。
2. **版本不可追溯**：App 内 versionName 仍 `0.1.0-week1` / versionCode 1，
   用户反馈时无法从 App 内辨认构建，只能靠 Release tag。

## 方案（具体、可验证、不换包名/不清存档）

### A. 固定测试签名（覆盖安装友好）

1. 本地一次性生成专用测试 keystore（**不进入仓库**）：
   `keytool -genkeypair -v -keystore sensewalk-test.jks -alias test \
    -keyalg RSA -keysize 2048 -validity 10950 -storetype JKS`
2. Base64 后存为 GitHub Actions secret `TEST_SIGNING_KEYSTORE`（连同
   `TEST_SIGNING_STORE_PASSWORD`/`TEST_SIGNING_KEY_PASSWORD` 两个 secret）。
3. `app/build.gradle.kts` 增加条件签名配置（secret 缺失时回退 debug 签名，
   本地开发不受影响）：
   ```kotlin
   val ks = System.getenv("TEST_SIGNING_KEYSTORE") // CI 侧由 workflow 注入
   signingConfigs {
       if (ks != null) {
           create("ciTest") {
               storeBytes = Base64.getDecoder().decode(ks).inputStream().readBytes()
               storePassword = System.getenv("TEST_SIGNING_STORE_PASSWORD")
               keyAlias = "test"
               keyPassword = System.getenv("TEST_SIGNING_KEY_PASSWORD")
           }
       }
   }
   // android.buildTypes["debug"] 的 signingConfig 在 ks 非空时指向 ciTest
   ```
   workflow 用 `env` 把 secret 传入 gradle（不落盘、不 echo）。
4. 效果：所有后续 build 同证书——**覆盖安装成功、用户存档保留**；
   keystore 私钥只在 secret，泄漏面最小（测试钥，非商店发布钥）。
5. 验证：两个连续 build 的 APK `apksigner verify --print-certs` 指纹一致 +
   模拟器覆盖安装成功且旧快照仍在。

### B. 版本追溯（App 内可辨认构建）

在 CI workflow 里以 `-PversionNameSuffix=+build.NNN.<sha7>` 形式注入：
versionName 变为 `0.1.0-week1+build.176.aaa789b`（versionCode 递增由
workflow run number 提供 `-PversionCodeOverride`）。设置页与结果页展示
BuildConfig.VERSION_NAME。**不改变包名**；versionCode 单调递增保证覆盖
安装的方向性校验通过。

## 实施时机

属于生产构建配置改动（业务 CI/Gradle 归 zcode 所有），但当前阶段包
build-176 已冻结发布——**本轮不实施**，作为提案交 QA 纳入下个阶段的
补丁或发布流程任务；实施时走独立分支+新 build，不替换既有包二进制。
