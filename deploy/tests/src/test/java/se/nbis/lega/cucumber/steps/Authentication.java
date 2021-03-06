package se.nbis.lega.cucumber.steps;

import cucumber.api.java8.En;
import lombok.extern.slf4j.Slf4j;
import net.schmizz.sshj.SSHClient;
import net.schmizz.sshj.common.Buffer;
import net.schmizz.sshj.sftp.SFTPException;
import net.schmizz.sshj.transport.verification.PromiscuousVerifier;
import net.schmizz.sshj.userauth.UserAuthException;
import net.schmizz.sshj.userauth.keyprovider.KeyPairWrapper;
import org.apache.commons.io.FileUtils;
import org.junit.Assert;
import se.nbis.lega.cucumber.Context;
import se.nbis.lega.cucumber.Utils;

import java.io.File;
import java.io.IOException;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;

@Slf4j
public class Authentication implements En {

    public Authentication(Context context) {
        Utils utils = context.getUtils();

        Given("^I have an account at Central EGA$", () -> {
            String cegaUsersFolderPath = utils.getPrivateFolderPath() + "/cega/users/" + utils.getProperty("instance.name");
            String user = context.getUser();
            try {
                generateKeypair(context);
                byte[] keyBytes = new Buffer.PlainBuffer().putPublicKey(context.getKeyProvider().getPublic()).getCompactData();
                String publicKey = Base64.getEncoder().encodeToString(keyBytes);
                File userYML = new File(String.format(cegaUsersFolderPath + "/%s.yml", user));
                FileUtils.writeLines(userYML, Arrays.asList("---",
                        "username: " + user,
                        "uid: " + Math.abs(new SecureRandom().nextInt()),
                        "gecos: EGA User " + user,
                        "pubkey: ssh-rsa " + publicKey));
            } catch (IOException e) {
                log.error(e.getMessage(), e);
            }
        });

        Given("^I have correct private key$",
                () -> {
                    if (context.getKeyProvider() == null) {
                        generateKeypair(context);
                    }
                });

        Given("^I have incorrect private key$", () -> generateKeypair(context));

//        Given("^inbox is deleted for my user$", () -> {
//            try {
//                utils.removeUserInbox(context.getUser());
//            } catch (InterruptedException e) {
//                log.error(e.getMessage(), e);
//            }
//        });

        Given("^file is removed from the inbox$", () -> {
            try {
                utils.removeUploadedFileFromInbox(context.getUser(), context.getEncryptedFile().getName());
            } catch (InterruptedException e) {
                log.error(e.getMessage(), e);
            }
        });

        When("^I connect to the LocalEGA inbox via SFTP using private key$", () -> connect(context));

        When("^I disconnect from the LocalEGA inbox$", () -> disconnect(context));

        When("^I am disconnected from the LocalEGA inbox$", () -> Assert.assertFalse(isConnected(context)));

//        When("^inbox is not created for me$", () -> {
//            try {
//                disconnect(context);
//                utils.removeUserInbox(context.getUser());
//                connect(context);
//            } catch (InterruptedException e) {
//                log.error(e.getMessage(), e);
//            }
//        });

        Then("^I'm logged in successfully$", () -> Assert.assertFalse(context.isAuthenticationFailed()));

        Then("^authentication fails$", () -> Assert.assertTrue(context.isAuthenticationFailed()));

    }

    private void generateKeypair(Context context) {
        try {
            KeyPairGenerator keyPairGenerator = KeyPairGenerator.getInstance("RSA");
            keyPairGenerator.initialize(2048, new SecureRandom());
            KeyPair keyPair = keyPairGenerator.genKeyPair();
            context.setKeyProvider(new KeyPairWrapper(keyPair));
        } catch (NoSuchAlgorithmException e) {
            log.error(e.getMessage(), e);
        }
    }

    private void connect(Context context) {
        try {
            SSHClient ssh = new SSHClient();
            ssh.addHostKeyVerifier(new PromiscuousVerifier());
            ssh.connect("localhost", Integer.parseInt(context.getUtils().readTraceProperty("DOCKER_PORT_inbox")));
            ssh.authPublickey(context.getUser(), context.getKeyProvider());
            context.setSsh(ssh);
            context.setSftp(ssh.newSFTPClient());
            context.setAuthenticationFailed(false);
        } catch (UserAuthException | SFTPException e) {
            context.setAuthenticationFailed(true);
        } catch (IOException e) {
            log.error(e.getMessage(), e);
        }
    }

    private boolean isConnected(Context context) {
        return context.getSsh().isConnected();
    }

    private void disconnect(Context context) {
        try {
            context.getSftp().close();
            context.getSsh().disconnect();
        } catch (Exception e) {
            log.error(e.getMessage(), e);
        }
    }

}
