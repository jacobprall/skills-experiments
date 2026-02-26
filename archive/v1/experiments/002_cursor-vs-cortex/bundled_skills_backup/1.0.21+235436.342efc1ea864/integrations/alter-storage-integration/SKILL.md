---
name: alter-storage-integration
description: >
  Modify properties of an existing storage integration (Amazon S3, Google Cloud Storage, or Azure Blob Storage)
---

# ALTER STORAGE INTEGRATION


Modifies the properties for an existing storage integration.

## Syntax

```sql
ALTER STORAGE INTEGRATION [ IF EXISTS ] <name> SET
  [ cloudProviderParams ]
  [ ENABLED = { TRUE | FALSE } ]
  [ STORAGE_ALLOWED_LOCATIONS = ('<cloud>://<bucket>/<path>/' [ , '<cloud>://<bucket>/<path>/' ... ] ) ]
  [ STORAGE_BLOCKED_LOCATIONS = ('<cloud>://<bucket>/<path>/' [ , '<cloud>://<bucket>/<path>/' ... ] ) ]
  [ COMMENT = '<string_literal>' ]
```

```sql
ALTER STORAGE INTEGRATION [ IF EXISTS ] <name> SET TAG <tag_name> = '<tag_value>' [ , <tag_name> = '<tag_value>' ... ]
```

```sql
ALTER STORAGE INTEGRATION <name> UNSET TAG <tag_name> [ , <tag_name> ... ]
```

```sql
ALTER STORAGE INTEGRATION [ IF EXISTS ] <name>  UNSET {
                                                          ENABLED                   |
                                                          STORAGE_BLOCKED_LOCATIONS |
                                                          COMMENT
                                                          }
                                                          [ , ... ]
```

Where:

```sql
cloudProviderParams (for Amazon S3) ::=
  STORAGE_AWS_ROLE_ARN = '<iam_role>'
  [ STORAGE_AWS_OBJECT_ACL = 'bucket-owner-full-control' ]
  [ STORAGE_AWS_EXTERNAL_ID = '<external_id>' ]
  [ USE_PRIVATELINK_ENDPOINT = { TRUE | FALSE } ]
```

```sql
cloudProviderParams (for Microsoft Azure) ::=
  AZURE_TENANT_ID = '<tenant_id>'
  [ USE_PRIVATELINK_ENDPOINT = { TRUE | FALSE } ]
```

## Parameters

- **`<name>`**

    Identifier for the integration to alter. If the identifier contains spaces or special characters, the entire string must be enclosed in double quotes. Identifiers enclosed in double quotes are also case-sensitive.

- **SET ...**

    Specifies one or more properties/parameters to set for the table (separated by blank spaces, commas, or new lines):

  - **ENABLED = { TRUE | FALSE }**

    Specifies whether this storage integration is available for usage in stages.

    - `TRUE` allows users to create new stages that reference this integration. Existing stages that reference this integration function normally.

    - `FALSE` prevents users from creating new stages that reference this integration. Existing stages that reference this integration cannot access the storage location in the stage definition.

  - **STORAGE_ALLOWED_LOCATIONS = ( '<cloud_specific_url>' )**

    Explicitly limits external stages that use the integration to reference one or more storage locations (Amazon S3, Google Cloud Storage, or Microsoft Azure). Supports a comma-separated list of URLs for existing buckets and, optionally, paths used to store data files for loading/unloading. Alternatively supports the `*` wildcard, meaning "allow access to all buckets and/or paths".

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

    - <account> is the name of the Azure account (e.g. `myaccount`). Use the `blob.core.windows.net` endpoint for all supported types of Azure blob storage accounts, including Data Lake Storage Gen2.

    - <container> is the name of the Azure container that stores your data files (e.g. `mycontainer`).

    - <path> is an optional case-sensitive path for files in the cloud storage location (i.e. files have names that begin with a common string) that limits access to a set of files. Paths are alternatively called *prefixes* or *folders* by different cloud storage services.

  - **STORAGE_BLOCKED_LOCATIONS = ( '<cloud_specific_url>' )**

    Explicitly prohibits external stages that use the integration from referencing one or more storage locations (Amazon S3, Google Cloud Storage, Microsoft Azure). Supports a comma-separated list of URLs for existing storage locations and, optionally, paths used to store data files for loading/unloading. Commonly used when STORAGE_ALLOWED_LOCATIONS is set to the `*` wildcard, allowing access to all buckets in your account *except for* blocked storage locations and, optionally, paths.

    Note

    Make sure to enclose only individual cloud storage location URLs in quotes. If you enclose the entire `STORAGE_BLOCKED_LOCATIONS` value in quotes, the value is invalid. As a result, the `STORAGE_BLOCKED_LOCATIONS` parameter setting is ignored when users create stages that reference the storage integration.

    **Amazon S3**

    `STORAGE_BLOCKED_LOCATIONS = ( '<protocol>://<bucket>/<path>/' [ , '<protocol>://<bucket>/<path>/' ... ] )`

    - <protocol> is one of the following:

      - `s3` refers to S3 storage in public AWS regions outside of China.

      - `s3china` refers to S3 storage in public AWS regions in China.

      - `s3gov` refers to S3 storage in government regions.

    - <bucket> is the name of an S3 bucket that stores your data files (e.g. `mybucket`).

    - <path> is an optional path (or *directory*) in the bucket that further limits access to data files.

    **Google Cloud Storage**

    `STORAGE_BLOCKED_LOCATIONS = ( 'gcs://<bucket>/<path>/' [ , 'gcs://<bucket>/<path>/' ... ] )`

    - <bucket> is the name of a GCS bucket that stores your data files (e.g. `mybucket`).

    - <path> is an optional path (or *directory*) in the bucket that further limits access to data files.

    **Microsoft Azure**

    `STORAGE_BLOCKED_LOCATIONS = ( 'azure://<account>.blob.core.windows.net/<container>/<path>/' [ , 'azure://<account>.blob.core.windows.net/<container>/<path>/' ... ] )`

    - <account> is the name of the Azure account (e.g. `myaccount`).

    - <container> is the name of the Azure container that stores your data files (e.g. `mycontainer`).

    - <path> is an optional path (or *directory*) in the container that further limits access to data files.

  - **TAG <tag_name> = '<tag_value>' [ , <tag_name> = '<tag_value>' , ... ]**

    Specifies the tag name and the tag string value.

    The tag value is always a string, and the maximum number of characters for the tag value is 256.

    For information about specifying tags in a statement, see Tag quotas.

  - **COMMENT = '<string_literal>'**

    String (literal) that specifies a comment for the integration.

- **UNSET ...**

    Specifies one or more properties/parameters to unset for the storage integration, which resets them back to their defaults:

  - `ENABLED`

  - `STORAGE_BLOCKED_LOCATIONS`

  - `TAG` <tag_name> [ , <tag_name> ... ]

  - `COMMENT`

## Cloud provider parameters (cloudProviderParams)

**Amazon S3**

**STORAGE_AWS_ROLE_ARN = '<iam_role>'**

Specifies the Amazon Resource Name (ARN) of the AWS identity and access management (IAM) role that grants privileges on the S3 bucket containing your data files. For more information, see Configuring secure access to Amazon S3.

**STORAGE_AWS_OBJECT_ACL = 'bucket-owner-full-control'**

Enables support for AWS access control lists (ACLs) to grant the S3 bucket owner full control. Files created in Amazon S3 buckets from unloaded table data are owned by an AWS Identity and Access Management (IAM) role. ACLs support the use case where IAM roles in one AWS account are configured to access S3 buckets in one or more other AWS accounts. Without ACL support, users in the bucket-owner accounts could not access the data files unloaded to an external (S3) stage using a storage integration.

When users unload Snowflake table data to data files in an S3 stage using COPY INTO <location>, the unload operation applies an ACL to the unloaded data files. The data files apply the `"s3:x-amz-acl":"bucket-owner-full-control"` privilege to the files, granting the S3 bucket owner full control over them.

**STORAGE_AWS_EXTERNAL_ID = '<external_id>'**

Specifies an external ID that Snowflake uses to establish a trust relationship with AWS. You must specify the same external ID in the trust policy of the IAM role that you configured for this storage integration. For more information, see How to use an external ID when granting access to your AWS resources to a third party.

**USE_PRIVATELINK_ENDPOINT = { TRUE | FALSE }**

Specifies whether to use outbound private connectivity to harden your security posture. For information about using this parameter, see Private connectivity to external stages for Amazon Web Services.

**Microsoft Azure**

**AZURE_TENANT_ID = '<tenant_id>'**

Specifies the ID for your Office 365 tenant that the allowed and blocked storage accounts belong to. A storage integration can authenticate to only one tenant, and so the allowed and blocked storage locations must refer to storage accounts that all belong this tenant.

To find your tenant ID, log into the Azure portal and click Azure Active Directory >> Properties. The tenant ID is displayed in the Tenant ID field.

**USE_PRIVATELINK_ENDPOINT = { TRUE | FALSE }**

Specifies whether to use outbound private connectivity to harden your security posture. For information about using this parameter, see Private connectivity to external stages and Snowpipe automation for Microsoft Azure.

## Usage notes

Regarding metadata:

Attention

Customers should ensure that no personal data (other than for a User object), sensitive data, export-controlled data, or other regulated data is entered as metadata when using the Snowflake service. For more information, see Metadata fields in Snowflake.

## Examples

The following example initiates operation of a suspended integration:

```sql
ALTER STORAGE INTEGRATION myint SET ENABLED = TRUE;
```
