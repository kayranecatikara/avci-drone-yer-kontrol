---@meta

---@class UBlueprintFileUtilsBPLibrary : UBlueprintFunctionLibrary
local UBlueprintFileUtilsBPLibrary = {}

---@param DestFilename FString
---@param SrcFilename FString
---@param bReplace boolean
---@param bEvenIfReadOnly boolean
---@return boolean
function UBlueprintFileUtilsBPLibrary:MoveFile(DestFilename, SrcFilename, bReplace, bEvenIfReadOnly) end
---@param Path FString
---@param bCreateTree boolean
---@return boolean
function UBlueprintFileUtilsBPLibrary:MakeDirectory(Path, bCreateTree) end
---@return FString
function UBlueprintFileUtilsBPLibrary:GetUserDirectory() end
---@param StartDirectory FString
---@param FoundPaths TArray<FString>
---@param Wildcard FString
---@param bFindFiles boolean
---@param bFindDirectories boolean
---@return boolean
function UBlueprintFileUtilsBPLibrary:FindRecursive(StartDirectory, FoundPaths, Wildcard, bFindFiles, bFindDirectories) end
---@param Directory FString
---@param FoundFiles TArray<FString>
---@param FileExtension FString
---@return boolean
function UBlueprintFileUtilsBPLibrary:FindFiles(Directory, FoundFiles, FileExtension) end
---@param Filename FString
---@return boolean
function UBlueprintFileUtilsBPLibrary:FileExists(Filename) end
---@param Directory FString
---@return boolean
function UBlueprintFileUtilsBPLibrary:DirectoryExists(Directory) end
---@param Filename FString
---@param bMustExist boolean
---@param bEvenIfReadOnly boolean
---@return boolean
function UBlueprintFileUtilsBPLibrary:DeleteFile(Filename, bMustExist, bEvenIfReadOnly) end
---@param Directory FString
---@param bMustExist boolean
---@param bDeleteRecursively boolean
---@return boolean
function UBlueprintFileUtilsBPLibrary:DeleteDirectory(Directory, bMustExist, bDeleteRecursively) end
---@param DestFilename FString
---@param SrcFilename FString
---@param bReplace boolean
---@param bEvenIfReadOnly boolean
---@return boolean
function UBlueprintFileUtilsBPLibrary:CopyFile(DestFilename, SrcFilename, bReplace, bEvenIfReadOnly) end


