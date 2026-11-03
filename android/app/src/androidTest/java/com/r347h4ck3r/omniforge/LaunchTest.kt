package com.r347h4ck3r.omniforge
import android.content.Intent
import android.content.pm.ActivityInfo
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import org.junit.Assert.*
import org.junit.Test
class LaunchTest {
    @Test fun nativeRuntimeLoadsAndRejectsMissingModel(){
        try {NativeModel.generate("/nonexistent/model.gguf","hello",1);fail("Missing model accepted")}
        catch(expected:IllegalStateException){assertTrue(expected.message!!.contains("failed to load"))}
    }
    @Test fun offlineInferenceProducesText(){
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val model=java.io.File(instrumentation.targetContext.cacheDir,"smoke.gguf")
        instrumentation.context.assets.open("test-model.gguf").use{input->model.outputStream().use{input.copyTo(it)}}
        try {val result=NativeModel.generate(model.path,"Once upon a time",2);assertTrue(result.isNotBlank());assertFalse(result.contains("failed",true))}finally{model.delete()}
    }
    @Test fun appLaunchesAndRemoteModesAreLandscape(){
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        context.startActivity(Intent(context,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        val device=UiDevice.getInstance(instrumentation)
        assertNotNull(device.wait(Until.findObject(By.text("OmniForge")),15000))
        val info=context.packageManager.getActivityInfo(android.content.ComponentName(context,RemoteActivity::class.java),0)
        assertEquals(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE,info.screenOrientation)
        device.findObject(By.text("Remote")).click()
        assertNotNull(device.wait(Until.findObject(By.text("Open desktop")),5000))
        assertNotNull(device.findObject(By.text("Open terminal")))
    }
}
