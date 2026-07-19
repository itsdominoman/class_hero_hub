package com.classherohub.app;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class SystemInsetsPluginTest {
    @Test
    public void convertsPhysicalNavigationInsetToCssPixels() {
        assertEquals(48.0, SystemInsetsPlugin.cssPixels(144, 3.0f), 0.001);
        assertEquals(24.0, SystemInsetsPlugin.cssPixels(60, 2.5f), 0.001);
    }
}
