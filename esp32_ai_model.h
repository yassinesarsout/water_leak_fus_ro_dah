// Auto-generated XGBoost Model for ESP32 (IoT Spark 4.0 - Fus Ro Dah)
const char* predictLeakState(float w1, float w2, float w3, float w4, float w5, float h_mean) {
  float w_mean = (w1 + w2 + w3 + w4 + w5) / 5.0f;
  float w_delta = w5 - w1;
  float scores[4] = {0.0f};

  // Tree 0 (Class 0: NORMAL)
  if (w_mean < 155.80f) {
    scores[0] += 0.551020f;
  } else {
    scores[0] += -0.194245f;
  }

  // Tree 1 (Class 1: HUMID_AIR)
  if (h_mean < 82.90f) {
    scores[1] += -0.194245f;
  } else {
    scores[1] += 0.551020f;
  }

  // Tree 2 (Class 2: SMALL_SPILL)
  if (w1 < 775.00f) {
    scores[2] += -0.192233f;
  } else {
    if (w_delta < 24.00f) {
      scores[2] += 0.551020f;
    } else {
      scores[2] += -0.180000f;
    }
  }

  // Tree 3 (Class 3: LEAK)
  if (w_delta < 690.00f) {
    scores[3] += -0.194245f;
  } else {
    scores[3] += 0.551020f;
  }

  // Tree 4 (Class 0: NORMAL)
  if (w_mean < 155.80f) {
    scores[0] += 0.340311f;
  } else {
    scores[0] += -0.180123f;
  }

  // Tree 5 (Class 1: HUMID_AIR)
  if (h_mean < 82.90f) {
    scores[1] += -0.180123f;
  } else {
    scores[1] += 0.340311f;
  }

  // Tree 6 (Class 2: SMALL_SPILL)
  if (w1 < 775.00f) {
    scores[2] += -0.178042f;
  } else {
    if (w_delta < 24.00f) {
      scores[2] += 0.340180f;
    } else {
      scores[2] += -0.165358f;
    }
  }

  // Tree 7 (Class 3: LEAK)
  if (w_delta < 690.00f) {
    scores[3] += -0.180154f;
  } else {
    scores[3] += 0.340956f;
  }

  // Tree 8 (Class 0: NORMAL)
  if (w_mean < 155.80f) {
    scores[0] += 0.259661f;
  } else {
    scores[0] += -0.169707f;
  }

  // Tree 9 (Class 1: HUMID_AIR)
  if (h_mean < 82.90f) {
    scores[1] += -0.169707f;
  } else {
    scores[1] += 0.259661f;
  }

  // Tree 10 (Class 2: SMALL_SPILL)
  if (w1 < 775.00f) {
    scores[2] += -0.167389f;
  } else {
    if (w_delta < 24.00f) {
      scores[2] += 0.259513f;
    } else {
      scores[2] += -0.153595f;
    }
  }

  // Tree 11 (Class 3: LEAK)
  if (w_delta < 690.00f) {
    scores[3] += -0.169747f;
  } else {
    scores[3] += 0.260397f;
  }

  // Tree 12 (Class 0: NORMAL)
  if (w_mean < 155.80f) {
    scores[0] += 0.217007f;
  } else {
    scores[0] += -0.161487f;
  }

  // Tree 13 (Class 1: HUMID_AIR)
  if (h_mean < 82.90f) {
    scores[1] += -0.161487f;
  } else {
    scores[1] += 0.217007f;
  }

  // Tree 14 (Class 2: SMALL_SPILL)
  if (w1 < 775.00f) {
    scores[2] += -0.158799f;
  } else {
    if (w_delta < 24.00f) {
      scores[2] += 0.216855f;
    } else {
      scores[2] += -0.143374f;
    }
  }

  // Tree 15 (Class 3: LEAK)
  if (w_delta < 690.00f) {
    scores[3] += -0.161529f;
  } else {
    scores[3] += 0.217756f;
  }

  // Tree 16 (Class 0: NORMAL)
  if (w_mean < 155.80f) {
    scores[0] += 0.190785f;
  } else {
    scores[0] += -0.154655f;
  }

  // Tree 17 (Class 1: HUMID_AIR)
  if (h_mean < 82.90f) {
    scores[1] += -0.154655f;
  } else {
    scores[1] += 0.190785f;
  }

  // Tree 18 (Class 2: SMALL_SPILL)
  if (w1 < 775.00f) {
    scores[2] += -0.151475f;
  } else {
    if (w_delta < 24.00f) {
      scores[2] += 0.190631f;
    } else {
      scores[2] += -0.134015f;
    }
  }

  // Tree 19 (Class 3: LEAK)
  if (w_delta < 690.00f) {
    scores[3] += -0.154697f;
  } else {
    scores[3] += 0.191541f;
  }

  int best_class = 0;
  for (int i = 1; i < 4; i++) {
    if (scores[i] > scores[best_class]) best_class = i;
  }
  const char* labels[4] = {"NORMAL", "HUMID_AIR", "SMALL_SPILL", "LEAK"};
  return labels[best_class];
}