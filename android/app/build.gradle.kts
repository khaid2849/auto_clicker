import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "io.github.khaid2849.autoclicker"
    compileSdk = 36

    defaultConfig {
        applicationId = "io.github.khaid2849.autoclicker"
        minSdk = 24 // Android 7.0: the first version that lets an accessibility service send taps
        targetSdk = 36
        versionCode = 2
        versionName = "1.2.0"
    }

    // Release signing comes from 4 environment variables (CI fills them from GitHub secrets).
    // Without them the release APK is signed with this machine's debug key: fine for trying it,
    // but APKs signed with different keys can't be installed over each other.
    val keystoreFile = System.getenv("ANDROID_KEYSTORE_FILE")
    signingConfigs {
        if (!keystoreFile.isNullOrBlank()) {
            create("release") {
                storeFile = file(keystoreFile)
                storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            signingConfig = signingConfigs.findByName("release") ?: signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
