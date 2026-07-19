package com.classherohub.app;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import androidx.core.graphics.Insets;

import org.junit.Test;

public class MainActivityTest {
    @Test
    public void nativeBoundaryPreservesPhysicalSystemBarPixels() {
        Insets systemBars = Insets.of(0, 96, 0, 144);

        assertTrue(MainActivity.needsPaddingUpdate(0, 0, 0, 0, systemBars));
        assertFalse(MainActivity.needsPaddingUpdate(0, 96, 0, 144, systemBars));
    }

    @Test
    public void diagnosticReportsNativeAndAppliedShellInsets() {
        String diagnostic = MainActivity.insetDiagnostic(
                Insets.of(0, 96, 0, 144),
                96,
                144,
                3.0f
        );

        assertEquals(
                "topInset=96px bottomInset=144px shellTop=96px shellBottom=144px density=3.0",
                diagnostic
        );
    }
}
