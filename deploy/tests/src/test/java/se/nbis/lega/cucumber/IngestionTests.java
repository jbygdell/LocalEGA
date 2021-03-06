package se.nbis.lega.cucumber;

import cucumber.api.CucumberOptions;
import cucumber.api.junit.Cucumber;
import org.junit.runner.RunWith;

@RunWith(Cucumber.class)
@CucumberOptions(
        format = {"pretty", "html:target/cucumber"},
        features = {
                "src/test/resources/cucumber/features/authentication.feature",
                "src/test/resources/cucumber/features/uploading.feature",
                "src/test/resources/cucumber/features/ingestion.feature"
        }
)
public class IngestionTests {
}
