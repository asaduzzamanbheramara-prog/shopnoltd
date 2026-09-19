package com.shopnoltd.mobile

import org.junit.Test
import org.junit.Assert.assertTrue
import org.robolectric.annotation.Config

@Config(manifest = Config.NONE)
class RobolectricSmokeTest {
    @Test
    fun robolectric_smoke() {
        assertTrue(true)
    }
}
