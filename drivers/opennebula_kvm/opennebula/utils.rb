def inject_context_script(file_path)
    # TODO: Write me
end

def decompress(file, temp_path)
    # TODO: We need a more clever version of this
    filename = File.basename(file, ".*")
    target = File.join(temp_path, filename)
    system("gunzip -c #{file} > #{target}")
    return target
end
