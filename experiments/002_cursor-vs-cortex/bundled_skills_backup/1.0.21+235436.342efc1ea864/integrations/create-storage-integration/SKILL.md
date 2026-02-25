---
name: create-storage-integration
description: >
  Create a new storage integration for Amazon S3, Google Cloud Storage, or Microsoft Azure Blob Storage
---

# CREATE STORAGE INTEGRATION


Creates a new storage integration in the account or replaces an existing integration.

A storage integration is a Snowflake object that stores a generated identity and access management (IAM) entity for your external cloud storage, along with an optional set of allowed or blocked storage locations (Amazon S3, Google Cloud Storage, or Microsoft Azure). Cloud provider administrators in your organization grant permissions on the storage locations to the generated entity. This option allows users to avoid supplying credentials when creating stages or when loading or unloading data.

A single storage integration can support multiple external stages. The URL in the stage definition must align with the storage location specified for the STORAGE_ALLOWED_LOCATIONS parameter.

Note

- If your cloud storage is located on a different cloud platform from your Snowflake account, the storage location must be in the public cloud and not a virtual private environment.

  Snowflake charges a per-byte fee when you unload data from Snowflake into an external stage in a different region or different cloud provider. For details, see the pricing page.

- Accessing cloud storage in a government region using a storage integration is limited to Snowflake accounts hosted in the same government region.

  Similarly, if you need to access cloud storage in a region in China, you can use a storage integration only from a Snowflake account hosted in the same region in China.

  In these cases, use the CREDENTIALS parameter in the CREATE STAGE command (rather than using a storage integration) to provide the credentials for authentication.

## Syntax

```sql
CREATE [ OR REPLACE ] STORAGE INTEGRATION [IF NOT EXISTS]
  <name>
  TYPE = EXTERNAL_STAGE
  cloudProviderParams
  ENABLED = { TRUE | FALSE }
  STORAGE_ALLOWED_LOCATIONS = ('<cloud>://<bucket>/<path>/' [ , '<cloud>://<bucket>/<path>/' ... ] )
  [ STORAGE_BLOCKED_LOCATIONS = ('<cloud>://<bucket>/<path>/' [ , '<cloud>://<bucket>/<path>/' ... ] ) ]
  [ COMMENT = '<string_literal>' ]
```

Where:

```sql
cloudProviderParams (for Amazon S3) ::=
  STORAGE_PROVIDER = 'S3'
  STORAGE_AWS_ROLE_ARN = '<iam_role>'
  [ STORAGE_AWS_EXTERNAL_ID = '<external_id>' ]
  [ STORAGE_AWS_OBJECT_ACL = 'bucket-owner-full-control' ]
  [ USE_PRIVATELINK_ENDPOINT = { TRUE | FALSE } ]
```

```sql
cloudProviderParams (for Google Cloud Storage) ::=
  STORAGE_PROVIDER = 'GCS'
```

```sql
cloudProviderParams (for Microsoft Azure) ::=
  STORAGE_PROVIDER = 'AZURE'
  AZURE_TENANT_ID = '<tenant_id>'
  [ USE_PRIVATELINK_ENDPOINT = { TRUE | FALSE } ]
```

## Required parameters

- **<name>**
  String that specifies the identifier (i.e. name) for the integration; must be unique in your account.
  In addition, the identifier must start with an alphabetic character and cannot contain spaces or special characters unless the entire identifier string is enclosed in double quotes (e.g. `"My object"`). Identifiers enclosed in double quotes are also case-sensitive.
  For more details, see Identifier requirements.

- **TYPE = EXTERNAL_STAGE**
  Specify the type of integration:
  - `EXTERNAL_STAGE`: Creates an interface between Snowflake and an external cloud storage location.

- **ENABLED = { TRUE | FALSE }**
  Specifies whether this storage integration is available for usage in stages.
  - `TRUE` allows users to create new stages that reference this integration. Existing stages that reference this integration function normally.
  - `FALSE` prevents users from creating new stages that reference this integration. Existing stages that reference this integration cannot access the storage location in the stage definition.

- **STORAGE_ALLOWED_LOCATIONS = ( '<cloud_specific_url>' )**
  Explicitly limits external stages that use the integration to reference one or more storage locations (i.e. S3 bucket, GCS bucket, or Azure container). Supports a comma-separated list of URLs for existing buckets and, optionally, paths used to store data files for loading/unloading. Alternatively supports the `*` wildcard, meaning "allow access to all buckets and/or paths".

  **Amazon S3**

  `STORAGE_ALLOWED_LOCATIONS = ( '<protocol>://<bucket>/<path>/' [ , '<protocol>://<bucket>/<path>/' ... ] )`

  - <protocol> is one of the following:
    - `s3` refers to S3 storage in public AWS regions outside of China.
    - `s3china` refers to S3 storage in public AWS regions in China.
    - `s3gov` refers to S3 storage in government regions.
  - <bucket> is the name of an S3 bucket that stores your data files (e.g. `mybucket`).
  - <path> is an optional case-sensitive path for files in the cloud storage location (i.e. files have names that begin with a common string) that limits access to a set of files. Paths are alternatively called *prefixes* or *folders* by different cloud storage services.

  **Google Cloud Storage**

  `STORAGE_ALLOWED_LOCATIONS = ( 'gcs://<bucket>/<path>/' [ , 'gcs://<bucket>/<path>/' ... ] )`

  - <bucket> is the name of a GCS bucket that stores your data files (e.g. `mybucket`).
  - <path> is an optional case-sensitive path for files in the cloud storage location (i.e. files have names that begin with a common string) that limits access to a set of files. Paths are alternatively called *prefixes* or *folders* by different cloud storage services.

  **Microsoft Azure**

  `STORAGE_ALLOWED_LOCATIONS = ( 'azure://<account>.blob.core.windows.net/<container>/<path>/' [ , 'azure://<account>.blob.core.windows.net/<container>/<path>/' ... ] )`

  - <account> is the name of the Azure storage account (e.g. `myaccount`). Use the `blob.core.windows.net` endpoint for all supported types of Azure blob storage accounts, including Data Lake Storage Gen2.
  - <container> is the name of a Azure blob storage container that stores your data files (e.g. `mycontainer`).
  - <path> is an optional case-sensitive path for files in the cloud storage location (i.e. files have names that begin with a common string) that limits access to a set of files. Paths are alternatively called *prefixes* or *folders* by different cloud storage services.

  **Microsoft Fabric OneLake**

  `STORAGE_ALLOWED_LOCATIONS = ( 'azure://onelake.blob.fabric.microsoft.com/<workspace_id>/<item_id>/Files/<path>/' [ , ... ] )`

  - `onelake.blob.fabric.microsoft.com` is the global service root for OneLake. This single endpoint automatically routes requests to the correct geographical region where your data resides.
  - <workspace_id> is the unique 128-bit GUID of the Fabric Workspace; for example, `aab1c234-567d-8901-234e-fgh56789ij`.
  - <item_id> is the unique GUID of the specific Fabric item, such as a Lakehouse or Warehouse.
  - `Files` is the mandatory path segment for Lakehouse items. This segment points to the unmanaged section of the lake where you store raw data such as CSV, Parquet, or JSON.
  - <path> is an optional case-sensitive path to a specific folder or file prefix. Although optional, providing a path is recommended when loading specific datasets to improve performance and prevent accidental processing of unrelated files.

## Optional parameters

- **STORAGE_BLOCKED_LOCATIONS = ( '<cloud_specific_url>' )**
  Explicitly prohibits external stages that use the integration from referencing one or more storage locations (i.e. S3 buckets or GCS buckets). Supports a comma-separated list of URLs for existing storage locations and, optionally, paths used to store data files for loading/unloading. Commonly used when STORAGE_ALLOWED_LOCATIONS is set to the `*` wildcard, allowing access to all buckets in your account *except for* blocked storage locations and, optionally, paths.

  Note

  Make sure to enclose only individual cloud storage location URLs in quotes. If you enclose the entire `STORAGE_BLOCKED_LOCATIONS` value in quotes, the value is invalid. As a result, the `STORAGE_BLOCKED_LOCATIONS` parameter setting is ignored when users create stages that reference the storage integration.

  **Amazon S3**

  `STORAGE_BLOCKED_LOCATIONS = ( '<protocol>://<bucket>/<path>/' [ , '<protocol>://<bucket>/<path>/' ... ] )`

  - <protocol> is one of the following:
    - `s3` refers to S3 storage in public AWS regions outside of China.
    - `s3china` refers to S3 storage in public AWS regions in China.
    - `s3gov` refers to S3 storage in government regions.
  - <bucket> is the name of an S3 bucket that stores your data files (e.g. `mybucket`).
  - <path> is an optional path (or *directory*) in the bucket that further limits access to the data files.

  **Google Cloud Storage**

  `STORAGE_BLOCKED_LOCATIONS = ( 'gcs://<bucket>/<path>/' [ , 'gcs://<bucket>/<path>/' ... ] )`

  - <bucket> is the name of a GCS bucket that stores your data files (e.g. `mybucket`).
  - <path> is an optional path (or *directory*) in the bucket that further limits access to the data files.

  **Microsoft Azure**

  `STORAGE_BLOCKED_LOCATIONS = ( 'azure://<account>.blob.core.windows.net/<container>/<path>/' [ , 'azure://<account>.blob.core.windows.net/<container>/<path>/' ... ] )`

  - <account> is the name of the Azure storage account (e.g. `myaccount`).
  - <container> is the name of a Azure blob storage container that stores your data files (e.g. `mycontainer`).
  - <path> is an optional path (or *directory*) in the bucket that further limits access to the data files.

  **Microsoft Fabric OneLake**

  `STORAGE_BLOCKED_LOCATIONS = ( 'azure://onelake.blob.fabric.microsoft.com/<workspace_id>/<item_id>/Files/<path>/' [ , ... ] )`

  - <workspace_id> is the unique 128-bit GUID of the Fabric Workspace.
  - <item_id> is the unique GUID of the specific Fabric item.
  - `Files` is the path segment for Lakehouse items.
  - <path> is an optional path that further limits the blocked location.

- **COMMENT = '<string_literal>'**
  String (literal) that specifies a comment for the integration.
  Default: No value

## Cloud provider parameters (cloudProviderParams)

**Amazon S3**

- **STORAGE_PROVIDER = '{ S3 | S3CHINA | S3GOV }'**
  Specifies the cloud storage provider that stores your data files:
  - `'S3'`: S3 storage in public AWS regions outside of China.
  - `'S3CHINA'`: S3 storage in public AWS regions in China.
  - `'S3GOV'`: S3 storage in AWS government regions.

- **STORAGE_AWS_ROLE_ARN = '<iam_role>'**
  Specifies the Amazon Resource Name (ARN) of the AWS identity and access management (IAM) role that grants privileges on the S3 bucket containing your data files. For more information, see Configuring secure access to Amazon S3.

- **STORAGE_AWS_EXTERNAL_ID = '<external_id>'**
  Optionally specifies an external ID that Snowflake uses to establish a trust relationship with AWS. You must specify the same external ID in the trust policy of the IAM role that you configured for this storage integration. For more information, see How to use an external ID when granting access to your AWS resources to a third party.
  If you don't specify a value for this parameter, Snowflake automatically generates an external ID when you create the storage integration.

- **STORAGE_AWS_OBJECT_ACL = 'bucket-owner-full-control'**
  Enables support for AWS access control lists (ACLs) to grant the bucket owner full control. Files created in Amazon S3 buckets from unloaded table data are owned by an AWS Identity and Access Management (IAM) role. ACLs support the use case where IAM roles in one AWS account are configured to access S3 buckets in one or more other AWS accounts. Without ACL support, users in the bucket-owner accounts could not access the data files unloaded to an external (S3) stage using a storage integration.
  When users unload Snowflake table data to data files in an S3 stage using COPY INTO <location>, the unload operation applies an ACL to the unloaded data files. The data files apply the `"s3:x-amz-acl":"bucket-owner-full-control"` privilege to the files, granting the S3 bucket owner full control over them.

- **USE_PRIVATELINK_ENDPOINT = { TRUE | FALSE }**
  Specifies whether to use outbound private connectivity to harden your security posture. For information about using this parameter, see Private connectivity to external stages for Amazon Web Services.

**Google Cloud Storage**

- **STORAGE_PROVIDER = 'GCS'**
  Specifies the cloud storage provider that stores your data files.

**Microsoft Azure**

- **STORAGE_PROVIDER = 'AZURE'**
  Specifies the cloud storage provider that stores your data files.

- **AZURE_TENANT_ID = '<tenant_id>'**
  Specifies the ID for your Office 365 tenant that the allowed and blocked storage accounts belong to. A storage integration can authenticate to only one tenant, and so the allowed and blocked storage locations must refer to storage accounts that all belong this tenant.
  To find your tenant ID, log into the Azure portal and click Azure Active Directory >> Properties. The tenant ID is displayed in the Tenant ID field.

- **USE_PRIVATELINK_ENDPOINT = { TRUE | FALSE }**
  Specifies whether to use outbound private connectivity to harden your security posture. For information about using this parameter, see Private connectivity to external stages and Snowpipe automation for Microsoft Azure.

**Microsoft Fabric OneLake**

- **STORAGE_PROVIDER = 'AZURE'**
  Specifies the cloud storage provider. Use `'AZURE'` for Microsoft Fabric OneLake storage.

- **AZURE_TENANT_ID = '<tenant_id>'**
  Specifies the ID for your Microsoft Entra ID (formerly Azure Active Directory) tenant that the Fabric Workspace belongs to.

  Note

  Private connectivity endpoints (USE_PRIVATELINK_ENDPOINT) aren't supported for Microsoft Fabric OneLake storage locations.

## Access control requirements

A role used to execute this operation must have the following privileges at a minimum:

| Privilege | Object | Notes |
|---|---|---|
| CREATE INTEGRATION | Account | Only the ACCOUNTADMIN role has this privilege by default. The privilege can be granted to additional roles as needed. |

## Usage notes

Caution

Recreating a storage integration (using CREATE OR REPLACE STORAGE INTEGRATION) breaks the association between the storage integration and any stage that references it. This is because a stage links to a storage integration using a hidden ID rather than the name of the storage integration. Behind the scenes, the CREATE OR REPLACE syntax drops the object and recreates it with a different hidden ID.

If you must recreate a storage integration after it has been linked to one or more stages, you must reestablish the association between each stage and the storage integration by executing ALTER STAGE <stage_name> SET STORAGE_INTEGRATION = <storage_integration_name>, where:

- <stage_name> is the name of the stage.

- <storage_integration_name> is the name of the storage integration.

Regarding metadata:

Attention

Customers should ensure that no personal data (other than for a User object), sensitive data, export-controlled data, or other regulated data is entered as metadata when using the Snowflake service. For more information, see Metadata fields in Snowflake.

- The OR REPLACE and IF NOT EXISTS clauses are mutually exclusive. They can't both be used in the same statement.

- CREATE OR REPLACE <object> statements are atomic. That is, when an object is replaced, the old object is deleted and the new object is created in a single transaction.

## Examples

The following example creates an integration that explicitly limits external stages that use the integration to reference either of two buckets and paths:

**Amazon S3**

```sql
CREATE STORAGE INTEGRATION s3_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::001234567890:role/myrole'
  ENABLED = TRUE
  STORAGE_ALLOWED_LOCATIONS = ('s3://mybucket1/path1/', 's3://mybucket2/path2/');
```

If the S3 storage is in a public AWS region in China, use `'S3CHINA'` for the STORAGE_PROVIDER parameter and `s3china://` protocol in STORAGE_ALLOWED_LOCATIONS.

**Google Cloud Storage**

```sql
CREATE STORAGE INTEGRATION gcs_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'GCS'
  ENABLED = TRUE
  STORAGE_ALLOWED_LOCATIONS = ('gcs://mybucket1/path1/', 'gcs://mybucket2/path2/');
```

**Microsoft Azure**

```sql
CREATE STORAGE INTEGRATION azure_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'AZURE'
  ENABLED = TRUE
  AZURE_TENANT_ID = '<tenant_id>'
  STORAGE_ALLOWED_LOCATIONS = ('azure://myaccount.blob.core.windows.net/mycontainer/path1/', 'azure://myaccount.blob.core.windows.net/mycontainer/path2/');
```

The following example creates an integration that allows external stages that use the integration to reference *any* bucket and path in your account *except for* those that are explicitly blocked:

**Amazon S3**

```sql
CREATE STORAGE INTEGRATION s3_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::001234567890:role/myrole'
  ENABLED = TRUE
  STORAGE_ALLOWED_LOCATIONS = ('*')
  STORAGE_BLOCKED_LOCATIONS = ('s3://mybucket3/path3/', 's3://mybucket4/path4/');
```

If the S3 storage is in a public AWS region in China, use `'S3CHINA'` for the STORAGE_PROVIDER parameter and `s3china://` protocol in STORAGE_BLOCKED_LOCATIONS.

**Google Cloud Storage**

```sql
CREATE STORAGE INTEGRATION gcs_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'GCS'
  ENABLED = TRUE
  STORAGE_ALLOWED_LOCATIONS = ('*')
  STORAGE_BLOCKED_LOCATIONS = ('gcs://mybucket3/path3/', 'gcs://mybucket4/path4/');
```

**Microsoft Azure**

```sql
CREATE STORAGE INTEGRATION azure_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'AZURE'
  ENABLED = TRUE
  AZURE_TENANT_ID = 'a123b4c5-1234-123a-a12b-1a23b45678c9'
  STORAGE_ALLOWED_LOCATIONS = ('*')
  STORAGE_BLOCKED_LOCATIONS = ('azure://myaccount.blob.core.windows.net/mycontainer/path3/', 'azure://myaccount.blob.core.windows.net/mycontainer/path4/');
```
