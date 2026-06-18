import { PhotographyType, CropAspectRatio } from "../src/enums";

describe("PhotographyType enum", () => {
  it("has expected string values", () => {
    expect(PhotographyType.WEDDING).toBe("WEDDING");
    expect(PhotographyType.PORTRAITS).toBe("PORTRAITS");
    expect(PhotographyType.REAL_ESTATE).toBe("REAL_ESTATE");
    expect(PhotographyType.LANDSCAPE_NATURE).toBe("LANDSCAPE_NATURE");
    expect(PhotographyType.EVENTS).toBe("EVENTS");
    expect(PhotographyType.FAMILY_NEWBORN).toBe("FAMILY_NEWBORN");
    expect(PhotographyType.BOUDOIR).toBe("BOUDOIR");
    expect(PhotographyType.SPORTS).toBe("SPORTS");
    expect(PhotographyType.NO_TYPE).toBe("NO_TYPE");
    expect(PhotographyType.OTHER).toBe("OTHER");
  });

  it("covers all 10 types", () => {
    const values = Object.values(PhotographyType);
    expect(values).toHaveLength(10);
  });
});

describe("CropAspectRatio enum", () => {
  it("has expected values", () => {
    expect(CropAspectRatio.RATIO_2X3).toBe("2X3");
    expect(CropAspectRatio.RATIO_4X5).toBe("4X5");
    expect(CropAspectRatio.RATIO_5X7).toBe("5X7");
  });

  it("covers all 3 ratios", () => {
    expect(Object.values(CropAspectRatio)).toHaveLength(3);
  });
});
