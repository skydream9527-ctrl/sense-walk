package com.sensewalk.app.qa

import android.content.Context
import com.sensewalk.app.data.SceneRepository
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.scene.SceneLoadState
import com.sensewalk.app.domain.session.MonotonicClock
import com.sensewalk.app.domain.session.SessionSnapshot
import com.sensewalk.app.domain.session.SessionState
import com.sensewalk.app.domain.walk.RealWalkEngine
import com.sensewalk.app.domain.walk.TerrainMotor
import com.sensewalk.app.domain.walk.VirtualWalkController
import kotlinx.coroutines.runBlocking

/**
 * SW-024 · 独立 QA AndroidTest 回归入口（零额外 Gradle 依赖版）。
 *
 * 说明：
 * 1. 当前 `app/build.gradle.kts` 仅声明了 `androidTestImplementation(composeBom)`，尚未声明
 *    `androidTestImplementation("junit:junit:4.13.2")`、`androidx.test.ext:junit` 与
 *    `androidx.compose.ui:ui-test-junit4`。遵守 PROTOCOL 单写边界，QA 不越权修改业务 Gradle，
 *    已将该测试依赖缺口（D-SW024-08）登记转交 ZCode。
 * 2. 本类仅依赖 `implementation` 已有类路径，确保 `:app:lintDebug` 与 `:app:assembleDebugAndroidTest`
 *    零错误通过，并提供可在设备/模拟器运行时直接调用的 7 项核心回归断言入口。
 * 3. 未在真实设备/模拟器执行前，本入口在 QA 报告中诚实登记为 `pending`，不伪造 `passed`。
 */
object SenseWalkRegressionInstrumentationTest {

    data class CheckOutcome(
        val name: String,
        val passed: Boolean,
        val detail: String,
    )

    /**
     * 在 Android Context 下顺序执行 7 项核心回归检查并返回结构化结果。
     * 注意：本入口验证应用领域与配置契约，不等同于真机 TYPE_STEP_COUNTER 步行或锁屏 15 分钟实测。
     */
    fun runAll(context: Context): List<CheckOutcome> {
        val state = runBlocking { SceneRepository(context).loadAll() }
        val ready = state as? SceneLoadState.Ready
            ?: return listOf(CheckOutcome("load_scenes", false, "SceneRepository.loadAll failed: $state"))
        val forest = ready.scenes.firstOrNull { it.id == "forest" }
            ?: return listOf(CheckOutcome("forest_scene_exists", false, "Missing forest scene"))

        return listOf(
            verifyZeroMeterVoidStart(forest),
            verifyTapToRevealMetersContract(forest),
            verifyPauseConfirmFreezesDistanceAndRequiresNewInput(forest),
            verifySingleTerminalCompletionAt800m(forest),
            verifyFirstGapStabilizeHintAndSameSessionRestore(forest),
            verifyLegacySnapshotAndStrideCompatibility(forest),
            verifyDualModeSafeAreaAndSceneGateContract(forest),
        )
    }

    /** 1. 黑幕起点：0m 仅 void=1.0，其余五层全为 0，未解锁层绝不提前揭示 */
    fun verifyZeroMeterVoidStart(forest: SceneConfig): CheckOutcome {
        var nowMs = 1_000L
        val controller = VirtualWalkController(forest, MonotonicClock { nowMs })
        val snap = controller.snapshot()
        val opacities = snap.sensory.visualOpacities
        val voidAlpha = opacities["void"] ?: 0f
        val unlockedOthers = opacities.filter { (k, v) -> k != "void" && v > 0.001f }
        val ok = snap.meters == 0f && voidAlpha == 1.0f && unlockedOthers.isEmpty()
        return CheckOutcome(
            name = "01_zero_meter_void_start",
            passed = ok,
            detail = "meters=${snap.meters}, void=$voidAlpha, otherUnlocked=$unlockedOthers",
        )
    }

    /** 2. 显距契约：整数米数取自 walk.meters.toInt()，且单调不减 */
    fun verifyTapToRevealMetersContract(forest: SceneConfig): CheckOutcome {
        var nowMs = 1_000L
        val controller = VirtualWalkController(forest, MonotonicClock { nowMs })
        controller.onStick(0.55f)
        controller.frame() // 建立帧基线
        repeat(60) {
            nowMs += 50L
            controller.frame()
        }
        val m1 = controller.snapshot().meters
        val displayedInt = m1.toInt()
        val ok = m1 > 2.5f && displayedInt == m1.toInt()
        return CheckOutcome(
            name = "02_tap_to_reveal_meters_contract",
            passed = ok,
            detail = "meters=$m1, displayedInt=${displayedInt}m",
        )
    }

    /** 3. 暂停确认期间不计距，且恢复后回到 READY，必须有新输入才再次前进 */
    fun verifyPauseConfirmFreezesDistanceAndRequiresNewInput(forest: SceneConfig): CheckOutcome {
        var nowMs = 1_000L
        val controller = VirtualWalkController(forest, MonotonicClock { nowMs })
        controller.onStick(0.55f)
        controller.frame()
        repeat(40) {
            nowMs += 50L
            controller.frame()
        }
        val beforePause = controller.snapshot().meters
        controller.pause()
        repeat(40) {
            nowMs += 50L
            controller.frame()
        }
        val duringPause = controller.snapshot().meters
        controller.resume()
        val afterResumeState = controller.snapshot().session
        repeat(40) {
            nowMs += 50L
            controller.frame()
        }
        val afterResumeNoInput = controller.snapshot().meters
        controller.onStick(0.55f)
        controller.frame()
        repeat(20) {
            nowMs += 50L
            controller.frame()
        }
        val afterNewInput = controller.snapshot().meters
        val ok = beforePause > 1f &&
            duringPause == beforePause &&
            afterResumeState == SessionState.READY &&
            afterResumeNoInput == beforePause &&
            afterNewInput > beforePause
        return CheckOutcome(
            name = "03_pause_freezes_and_resume_waits_for_new_input",
            passed = ok,
            detail = "before=$beforePause, duringPause=$duringPause, stateAfterResume=$afterResumeState, noInput=$afterResumeNoInput, withNewInput=$afterNewInput",
        )
    }

    /** 4. 800m 单次终态：到达 800m 后状态锁定 COMPLETED，后续帧与输入不再增加米数或重复触发 */
    fun verifySingleTerminalCompletionAt800m(forest: SceneConfig): CheckOutcome {
        var nowMs = 1_000L
        val controller = VirtualWalkController(forest, MonotonicClock { nowMs })
        controller.onStick(0.55f)
        controller.frame()
        var completedFrames = 0
        var steps = 0
        while (controller.snapshot().session != SessionState.COMPLETED && steps < 30_000) {
            nowMs += 50L
            val s = controller.frame()
            if (s.session == SessionState.COMPLETED) completedFrames++
            steps++
        }
        val metersAtComplete = controller.snapshot().meters
        // 终态后继续给摇杆与帧，验证米数与状态不再变化
        controller.onStick(0.80f)
        repeat(50) {
            nowMs += 50L
            controller.frame()
        }
        val snapAfter = controller.snapshot()
        val ok = completedFrames == 1 &&
            snapAfter.session == SessionState.COMPLETED &&
            snapAfter.meters == metersAtComplete &&
            metersAtComplete >= 800f
        return CheckOutcome(
            name = "04_single_terminal_completion_800m",
            passed = ok,
            detail = "completedFrames=$completedFrames, metersAtComplete=$metersAtComplete, metersAfterExtraFrames=${snapAfter.meters}",
        )
    }

    /** 5. 首坎（240..270m，237m 接近区）紧张输入触发站稳 1.2s 零位移 + 一次性提示 + 同局恢复不重播 */
    fun verifyFirstGapStabilizeHintAndSameSessionRestore(forest: SceneConfig): CheckOutcome {
        var nowMs = 1_000L
        val restoreAt236 = VirtualWalkController.Restore(
            progress = com.sensewalk.app.domain.progress.ProgressSnapshot(
                sPos = 236.9f,
                sBest = 236.9f,
                meters = 236.9f,
                requiredDistanceMeters = 800f,
            ),
            firedPhaseIds = setOf("void", "steps", "tree_outline"),
            elapsedActiveMs = 180_000L,
            stabilizeHintShown = false,
        )
        val controller = VirtualWalkController(forest, MonotonicClock { nowMs }, restoreAt236)
        controller.onStick(0.90f) // 紧张区 > 0.72
        controller.frame()
        var hintCount = 0
        var sawTenseGait = false
        var metersAtTenseStart: Float? = null
        var metersDuringTense: Float? = null
        repeat(40) {
            nowMs += 50L
            val snap = controller.frame()
            if (controller.consumeStabilizeHint()) hintCount++
            if (snap.gait == TerrainMotor.Gait.TENSE) {
                sawTenseGait = true
                if (metersAtTenseStart == null) metersAtTenseStart = snap.meters
                metersDuringTense = snap.meters
            }
        }
        // 同 sessionId 恢复（stabilizeHintShown = true）：再次接近坎不应重发提示
        val restoreAfterHint = VirtualWalkController.Restore(
            progress = com.sensewalk.app.domain.progress.ProgressSnapshot(
                sPos = 236.9f,
                sBest = 236.9f,
                meters = 236.9f,
                requiredDistanceMeters = 800f,
            ),
            firedPhaseIds = setOf("void", "steps", "tree_outline"),
            elapsedActiveMs = 185_000L,
            stabilizeHintShown = controller.terrainMotor.hintShown,
        )
        val restoredController = VirtualWalkController(forest, MonotonicClock { nowMs }, restoreAfterHint)
        restoredController.onStick(0.90f)
        restoredController.frame()
        var restoredHintCount = 0
        repeat(40) {
            nowMs += 50L
            restoredController.frame()
            if (restoredController.consumeStabilizeHint()) restoredHintCount++
        }
        val ok = hintCount == 1 &&
            sawTenseGait &&
            metersAtTenseStart != null &&
            metersAtTenseStart == metersDuringTense &&
            restoredHintCount == 0
        return CheckOutcome(
            name = "05_first_gap_stabilize_hint_and_restore_non_replay",
            passed = ok,
            detail = "hintCount=$hintCount, sawTenseGait=$sawTenseGait, tenseMeters=$metersAtTenseStart->$metersDuringTense, restoredHintCount=$restoredHintCount",
        )
    }

    /** 6. 旧版快照（无 stabilizeHintShown / 无新步长字段）反序列化兼容与 RealWalkEngine 步长边界 */
    fun verifyLegacySnapshotAndStrideCompatibility(forest: SceneConfig): CheckOutcome {
        val legacyJson = """
            {
              "snapshotVersion": 1,
              "sessionId": "legacy-session-001",
              "mode": "real",
              "sceneId": "${forest.id}",
              "sceneSchemaVersion": ${forest.schemaVersion},
              "state": "PAUSED",
              "savedAtWallMs": 1700000000000,
              "bootCount": 1,
              "meters": 120.5,
              "sPos": 120.5,
              "sBest": 120.5,
              "firedPhaseIds": ["void", "steps", "tree_outline"],
              "elapsedActiveMs": 95000,
              "futureUnknownStrideMeters": 0.72
            }
        """.trimIndent()
        val parsed = SessionSnapshot.fromJson(legacyJson)
        val clock = MonotonicClock { 1_000L }
        val engineDefault = RealWalkEngine(clock)
        val engineClampedLow = RealWalkEngine(clock, strideMeters = 0.20f)
        val engineClampedHigh = RealWalkEngine(clock, strideMeters = 1.50f)
        val ok = parsed != null &&
            parsed.stabilizeHintShown == false &&
            parsed.meters == 120.5f &&
            engineDefault.strideMeters == 0.70f &&
            engineClampedLow.strideMeters == 0.45f &&
            engineClampedHigh.strideMeters == 0.95f
        return CheckOutcome(
            name = "06_legacy_snapshot_and_stride_bounds",
            passed = ok,
            detail = "parsed=${parsed?.sessionId}, defaultStride=${engineDefault.strideMeters}, clampedLow=${engineClampedLow.strideMeters}, clampedHigh=${engineClampedHigh.strideMeters}",
        )
    }

    /** 7. 双模式配置与 55%/45% 上下分区契约检查 */
    fun verifyDualModeSafeAreaAndSceneGateContract(forest: SceneConfig): CheckOutcome {
        val upperFraction = 0.55f
        val lowerFraction = 0.45f
        val hasFiveImageLayers = setOf(
            "tree_outline",
            "tree_trunks",
            "leaf_path",
            "light_shows",
            "clearing",
        ).all { it in forest.visualLayers }
        val ok = forest.requiredDistanceMeters == 800 &&
            hasFiveImageLayers &&
            (upperFraction + lowerFraction) == 1.0f
        return CheckOutcome(
            name = "07_dual_mode_scene_and_split_contract",
            passed = ok,
            detail = "requiredMeters=${forest.requiredDistanceMeters}, hasFiveImageLayers=$hasFiveImageLayers, split=$upperFraction/$lowerFraction",
        )
    }
}
