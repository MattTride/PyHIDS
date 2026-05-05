from pyhids.hasher import hash_file
import pytest




#文件正常
def test_hash_file(tmp_path):
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("hello")

    result = hash_file(test_file)

    assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

#文件使用了未知的hash算法
def test_hash_file_raises_on_unknown_algorithm(tmp_path):
    test_file = tmp_path / "x.txt"
    test_file.write_text("hi")

    with pytest.raises(ValueError):
        hash_file(test_file, algorithm="foo256")

#文件没有返回值
def test_file_returns_none_for_missing_file(tmp_path):
    missing = tmp_path / "ghost.txt"
    assert hash_file(missing) is None

#文件本身是一个目录
def test_file_returns_none_for_directory(tmp_path):
    assert hash_file(tmp_path) is None

