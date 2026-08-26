# Imagen AI Java SDK

Java SDK for the [Imagen AI](https://imagen-ai.com) photo-editing API. Mirrors the
Python, Node and Go SDKs: same endpoints, same workflow, same file-type rules.

- **Java 17+**, one runtime dependency (Jackson). HTTP uses the JDK's `java.net.http`.
- Blocking, thread-safe client. Concurrent uploads/downloads handled internally.
- Immutable records for every model; typed exceptions for every failure.

## Install (Maven)

```xml
<dependency>
  <groupId>com.imagen-ai</groupId>
  <artifactId>imagen-ai-sdk</artifactId>
  <version>1.2.0</version>
</dependency>
```

## Quick start

```java
import com.imagenai.*;
import java.util.List;

ImagenClient client = ImagenClient.builder("YOUR_API_KEY").build();

String uuid = client.createProject("My Photos");
client.uploadImages(uuid, List.of("photo1.dng", "photo2.dng"), null);

client.editAndWait(uuid, new EditRequest(profileKey), null);

List<DownloadLink> links = client.getDownloadLinks(uuid);
client.downloadFiles(links, "out", null);
```

### One-call workflow

```java
QuickEditResult result = client.quickEdit(QuickEditParams.builder()
        .projectName("Wedding")
        .profileKey(profileKey)
        .imagePaths(List.of("a.dng", "b.dng"))
        .photographyType(PhotographyType.WEDDING)
        .editOptions(EditOptions.builder().crop(true).smoothSkin(true).build())
        .export(true)
        .download(true)
        .downloadDir("out")
        .build());

System.out.println("Project: " + result.projectUuid());
System.out.println("Edited XMPs: " + result.downloadedFiles());
```

## Editing options

`EditOptions` mirrors the other SDKs. Unset options are omitted from the request
(never sent as `false`). Mutual-exclusivity rules are validated client-side:
at most one crop mode (`crop`, `headshotCrop`, `portraitCrop`) and at most one
straightening mode (`straighten`, `perspectiveCorrection`).

```java
EditOptions opts = EditOptions.builder()
        .crop(true)
        .cropAspectRatio(CropAspectRatio.R4X5)
        .hdrMerge(true)
        .skyReplacement(true)
        .skyReplacementTemplateId(templateId)
        .build();

client.editAndWait(uuid, new EditRequest(profileKey, PhotographyType.REAL_ESTATE, opts), null);
```

## Progress and concurrency

```java
UploadOptions up = UploadOptions.builder()
        .calculateMd5(true)
        .maxConcurrency(8)
        .progress((done, total, name) -> System.out.printf("%d/%d %s%n", done, total, name))
        .build();
UploadSummary summary = client.uploadImages(uuid, paths, up);
System.out.println(summary.successful() + "/" + summary.total() + " uploaded");
```

Poll tuning (exponential backoff, default first wait 5s capped at 30s):

```java
PollOptions poll = PollOptions.builder()
        .interval(Duration.ofSeconds(3))
        .progress(s -> System.out.println("progress: " + s.progress()))
        .build();
client.editAndWait(uuid, new EditRequest(profileKey), poll);
```

## Image-to-image (I2I)

Large files upload via S3 multipart automatically:

```java
String uuid = client.createI2IProject("Batch");
client.uploadI2IImages(uuid, paths, null);
client.startI2IEditing(uuid, I2IEditOptions.builder().hdrMerge(true).build());
List<DownloadLink> links = client.waitForI2ICompletion(uuid, null);
client.downloadFiles(links, "out", null);
```

## Enhance, copilot, finalize

```java
AIToolsResponse tools = client.getAITools(uuid, ProjectSource.REGULAR);
client.enhanceImage(uuid, "photo1.dng",
        new EnhanceRequest(tools.prompts().get(0).enhancementType(), ProjectSource.REGULAR));
client.copilot(uuid, "photo1.dng", new CopilotRequest("make it warmer", ProjectSource.REGULAR));
List<DownloadLink> finals = client.finalizeProject(uuid, ProjectSource.REGULAR);
```

## Errors

All errors are unchecked and extend `ImagenException`:

| Exception | When |
|-----------|------|
| `AuthenticationException` | 401 (invalid/missing API key) |
| `BadRequestException` | 400 |
| `ApiException` | any other non-2xx (`statusCode()`, `endpoint()`, `body()`) |
| `ProjectException` | editing reached a `Failed` status |
| `UploadException` / `DownloadException` | transfer failures |

Per-file upload failures are reported in `UploadSummary`, not thrown.

## Build

```bash
mvn -f sdks/java/pom.xml test     # run the test suite
mvn -f sdks/java/pom.xml package  # build the jar
```
