package com.sensewalk.app.engine.sensory

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.SoundPool
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import com.sensewalk.app.domain.scene.AudioLayerDef
import com.sensewalk.app.domain.scene.SceneConfig
import com.sensewalk.app.domain.sensory.SensoryBackend

/**
 * 感官后端的 Android 实现（T05）：
 * - 脚步 one-shot：SoundPool（低延迟，支持随机音高/音量）；
 * - 环境 loop：每层一个 MediaPlayer 循环播放，音量即淡入增益；
 * - 振动：Vibrator 波形（模式表见 [vibrationEffect]）。
 *
 * 素材现状（见 ASSETS.md）：场景配置的音频层当前全部为显式开发占位
 * （placeholder，无 file）——本实现会跳过占位层并在日志中说明，
 * 不伪造声音；素材入库后无需改代码即可播放。
 */
class AndroidSensoryBackend(
    private val context: Context,
    private val config: SceneConfig,
) : SensoryBackend {

    private val soundPool: SoundPool = SoundPool.Builder()
        .setMaxStreams(MAX_STREAMS)
        .setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_GAME)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build(),
        )
        .build()

    /** layerId → 已加载的 SoundPool id 列表（变体） */
    private val stepSounds = mutableMapOf<String, MutableList<Int>>()

    /** layerId → 循环播放器 */
    private val loops = mutableMapOf<String, MediaPlayer>()

    private val vibrator: Vibrator? = resolveVibrator()

    init {
        // 预加载脚步变体；占位层（无 files）记录后跳过
        for ((layerId, def) in config.layers) {
            if (def is AudioLayerDef.StepOneShot && def.files.isNotEmpty()) {
                val ids = mutableListOf<Int>()
                for (file in def.files) {
                    val id = loadSound(file)
                    if (id != null) ids.add(id)
                }
                if (ids.isNotEmpty()) stepSounds[layerId] = ids
                else Log.i(TAG, "脚步层 '$layerId' 素材未入库（占位），静默跳过")
            }
        }
    }

    override fun startLoop(layerId: String) {
        if (layerId in loops) return
        val def = config.layers[layerId] as? AudioLayerDef.Loop ?: return
        val file = def.file ?: run {
            Log.i(TAG, "环境层 '$layerId' 为开发占位（无 file），本轮不播放")
            return
        }
        try {
            val afd = context.assets.openFd(file)
            val player = MediaPlayer()
            player.setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
            afd.close()
            player.isLooping = true
            player.setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build(),
            )
            player.setVolume(0f, 0f)
            player.prepare()
            player.start()
            loops[layerId] = player
        } catch (e: Exception) {
            Log.w(TAG, "环境层 '$layerId' 播放失败（$file）：${e.message}")
        }
    }

    override fun setLoopGain(layerId: String, gain: Float) {
        loops[layerId]?.setVolume(gain.coerceIn(0f, 1f), gain.coerceIn(0f, 1f))
    }

    override fun playStep(layerId: String, variant: Int, volume: Float, pitchFactor: Float) {
        val ids = stepSounds[layerId] ?: return // 占位层：无声（ASSETS.md 记录）
        if (ids.isEmpty()) return
        val id = ids[variant.mod(ids.size)]
        soundPool.play(id, volume, volume, 1, 0, pitchFactor.coerceIn(0.5f, 2f))
    }

    override fun pauseAll() {
        loops.values.forEach { player ->
            runCatching { if (player.isPlaying) player.pause() }
        }
    }

    override fun resumeAll() {
        loops.values.forEach { player ->
            runCatching { if (!player.isPlaying) player.start() }
        }
    }

    override fun releaseAll() {
        loops.values.forEach { player ->
            runCatching {
                player.stop()
                player.release()
            }
        }
        loops.clear()
        runCatching { soundPool.release() }
    }

    override fun vibrate(patternId: String) {
        val effect = vibrationEffect(patternId) ?: return
        vibrator?.vibrate(effect)
    }

    override fun stopVibrate() {
        vibrator?.cancel()
    }

    private fun loadSound(file: String): Int? = try {
        val afd = context.assets.openFd(file)
        val id = soundPool.load(afd, 1)
        afd.close()
        if (id != 0) id else null // 0 = 加载失败
    } catch (e: Exception) {
        Log.w(TAG, "脚步素材加载失败（$file）：${e.message}")
        null
    }

    private fun resolveVibrator(): Vibrator? =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }

    /** 振动模式表（§7 各景单页定义；力度轻、跟步伐） */
    private fun vibrationEffect(patternId: String): VibrationEffect? = when (patternId) {
        "footstep_soft" -> VibrationEffect.createOneShot(24L, 90)
        "footstep_sand" -> VibrationEffect.createOneShot(32L, 70)
        "pulse_slow" -> VibrationEffect.createWaveform(longArrayOf(0L, 40L), intArrayOf(0, 60), -1)
        else -> {
            Log.i(TAG, "未知振动模式 '$patternId'，跳过")
            null
        }
    }

    private companion object {
        const val TAG = "SensoryBackend"
        const val MAX_STREAMS = 4
    }
}
