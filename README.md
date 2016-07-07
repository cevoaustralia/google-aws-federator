# Google AWS Federator

Tools to manage configuration and maintenance of federating identity between Google Apps (as the
identity provider) and AWS.

## Setup

### Prerequisites

1. Google Apps set up already. You're going to need to generate secrets for the federator.
1. You need to know your unique Google 'customer ID'. You can get this from the Google Admin
   Console, via `Security -> Set up Single Sign On (SSO)` -- the customer ID is the bit on the
   tail end of the Entity ID URL that looks like this:
   `https://accounts.google.com/o/saml2?idpid=XXXXXXXXX` (the "XXXXXXXXX" part)

### Configuration

1. You'll need to register the federator as an external app with Google Apps first:
    1. Log in to your Google Apps Developer Console via https://console.developers.google.com
    1. At the top of the page, there's a pulldown menu; by default, it's marked `Select a
       project`. If you click on it, you can choose `Create a Project`, which you should do
    1. Name the project `Federator` (you can call it something else, but you'll have to
       translate the rest of this documentation). You can change the App Engine location if it
       matters to you under `Advanced Options` but that's not required. You'll also have to
       agree to the T&Cs before creating the project, and choose whether to opt-in to the
       spam^H^H^H^Hmarketing emails.
    1. Click `Create` to create your new project.
    1. We will have to enable the admin APIs for this project before we create the credentials,
       so in the main API Manager screen, click `Admin SDK` under `Google Apps APIs` (you may
       have to click on the `More...` button underneath that heading). When the API screen
       appears, click `Enable`.
    1. Authentication and authorization for Federator will be via the OAuth2 
       [Installed Apps](https://developers.google.com/identity/protocols/OAuth2InstalledApp)
       pattern, so we will need to create some client identifiers. At the left-hand-side of the screen,
       click `Credentials` and then when the popup appears, choose `Create credential` and, from
       the pulldown menu, choose `OAuth2 Client ID`. From the selection of client types, choose
       `Other`, and set the client name to be `Federator CLI`. Click `Create`
    1. There'll be a popup which displays your OAuth2 Client ID and the client secret. Store
       these safely, as they will be used to identify your Federator CLI to Google.

### First Run

In order to grant access to the Federator to modify your Google Apps Domain Users, you'll need
to authenticate, via the OAuth2 browser flow, as a user who has the appropriate access.
The Federator will need to have access to modify custom user schemas (to create the schema
for the federated roles) and to modify users (to assign those roles from within the new
custom schema to users).

```
locahost$ federator init -I <client_id> -C <client_secret>
```

The script will cause a browser to be opened, where you can sign in as an appropriate user and
approve the access. Once this has been done once, the credentials will be stored in a file
`credentials.dat` -- however, these credentials expire after one hour after they become idle,
so if you're going to be doing this sort of thing a lot you'd probably be better off
batching things up.

### Subsequent Runs

Once the `credentials.dat` file has been created, you will not have to go through the browser
auth steps again while the credentials are valid.

## Usage

### Creating AWS SSO Schema

You can use Federator to add the required custom schema to your Google Apps Domain. This custom
schema is required to define the "shape" of the data that will be used when passing SAML
assertions from Google (as an Identity Provider, or IdP) to Amazon (as the Service Provider, or
SP).

TL;DR: Federator can make your Google Apps Domain the right shape to use AWS via Google Auth.

```
localhost$ federator schema -C <customerid> create
```

If the custom schema has already been created, nothing will be done. If the custom schema has
been created, but is the wrong "shape", then nothing will still be done. If you want to update
the custom schema, you will have to delete the existing one, and create a new one (see below for
`delete_schema` functionality)

### Deleting the AWS SSO Schema

Federator can "clean up" by removing the custom AWS SSO schema. Simply:

```
localhost$ federator schema -C <customerid> delete
```

If the custom schema has already been deleted, nothing will happen.

### Validating whether the custom AWS SSO Schema has been created

Federator can verify that the custom schema has been created:

```
localhost$ federator schema -C <customerid> verify
Schema exists
```

Federator will also return exit code 0 if the schema exists, and exit code 1 if it doesn't.
